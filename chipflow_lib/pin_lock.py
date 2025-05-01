# SPDX-License-Identifier: BSD-2-Clause
import inspect
import logging

from pprint import pformat
from pathlib import Path
from typing import Any, List, Dict, Tuple

from chipflow_lib import _parse_config, _ensure_chipflow_root, ChipFlowError
from chipflow_lib.platforms import (
        PACKAGE_DEFINITIONS,
        PIN_ANNOTATION_SCHEMA,
        top_interfaces,
        LockFile,
        Package,
        PortMap,
        Port
)
from chipflow_lib.config_models import Config

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


def count_member_pins(name: str, member: Dict[str, Any]) -> int:
    "Counts the pins from amaranth metadata"
    logger.debug(
        f"count_pins {name} {member['type']} "
        f"{member['annotations'] if 'annotations' in member else 'no annotations'}"
    )
    if member['type'] == 'interface' and 'annotations' in member \
       and PIN_ANNOTATION_SCHEMA in member['annotations']:
        return member['annotations'][PIN_ANNOTATION_SCHEMA]['width']
    elif member['type'] == 'interface':
        width = 0
        for n, v in member['members'].items():
            width += count_member_pins('_'.join([name, n]), v)
        return width
    elif member['type'] == 'port':
        return member['width']


def allocate_pins(name: str, member: Dict[str, Any], pins: List[str], port_name: str = None) -> Tuple[Dict[str, Port], List[str]]:
    "Allocate pins based of Amaranth member metadata"

    if port_name is None:
        port_name = name

    pin_map = {}

    logger.debug(f"allocate_pins: name={name}, pins={pins}")
    logger.debug(f"member={pformat(member)}")

    if member['type'] == 'interface' and 'annotations' in member \
       and PIN_ANNOTATION_SCHEMA in member['annotations']:
        logger.debug("matched IOSignature {sig}")
        sig = member['annotations'][PIN_ANNOTATION_SCHEMA]
        width = sig['width']
        options = sig['options']
        pin_map[name] = {'pins': pins[0:width],
                         'direction': sig['direction'],
                         'type': 'io',
                         'port_name': port_name,
                         'options': options}
        logger.debug(f"added '{name}':{pin_map[name]} to pin_map")
        return pin_map, pins[width:]
    elif member['type'] == 'interface':
        for k, v in member['members'].items():
            port_name = '_'.join([name, k])
            _map, pins = allocate_pins(k, v, pins, port_name=port_name)
            pin_map |= _map
            logger.debug(f"{pin_map},{_map}")
        return pin_map, pins
    elif member['type'] == 'port':
        logger.warning(f"Port '{name}' has no IOSignature, pin allocation likely to be wrong")
        width = member['width']
        pin_map[name] = {'pins': pins[0:width],
                              'direction': member['dir'],
                              'type': 'io',
                              'port_name': port_name
                              }
        logger.debug(f"added '{name}':{pin_map[name]} to pin_map")
        return pin_map, pins[width:]
    else:
        logging.debug(f"Shouldnt get here. member = {member}")
        assert False


def lock_pins() -> None:
    # Get the config as dict for backward compatibility with top_interfaces
    config_dict = _parse_config()

    # Parse with Pydantic for type checking and strong typing
    config_model = Config.model_validate(config_dict)

    used_pins = set()
    oldlock = None

    chipflow_root = _ensure_chipflow_root()
    lockfile = Path(chipflow_root, 'pins.lock')
    if lockfile.exists():
        json_string = lockfile.read_text()
        oldlock = LockFile.model_validate_json(json_string)

    print(f"Locking pins: {'using pins.lock' if lockfile.exists() else ''}")

    process = config_model.chipflow.silicon.process
    package_name = config_model.chipflow.silicon.package

    if package_name not in PACKAGE_DEFINITIONS:
        logger.debug(f"Package '{package_name} is unknown")
    package_type = PACKAGE_DEFINITIONS[package_name]

    package = Package(package_type=package_type)

    # Process pads and power configurations using Pydantic models
    for d in ("pads", "power"):
        logger.debug(f"Checking [chipflow.silicon.{d}]:")
        silicon_config = getattr(config_model.chipflow.silicon, d, {})
        for k, v in silicon_config.items():
            pin = str(v.loc)
            used_pins.add(pin)

            # Convert Pydantic model to dict for backward compatibility
            v_dict = {"type": v.type, "loc": v.loc}
            port = oldlock.package.check_pad(k, v_dict) if oldlock else None

            if port and port.pins != [pin]:
                raise ChipFlowError(
                    f"chipflow.toml conflicts with pins.lock: "
                    f"{k} had pin {port.pins}, now {[pin]}."
                )

            # Add pad to package
            package.add_pad(k, v_dict)

    logger.debug(f'Pins in use: {package_type.sortpins(used_pins)}')

    unallocated = package_type.pins - used_pins

    logger.debug(f"unallocated pins = {package_type.sortpins(unallocated)}")

    # Use the raw dict for top_interfaces since it expects the legacy format
    _, interfaces = top_interfaces(config_dict)

    logger.debug(f"All interfaces:\n{pformat(interfaces)}")

    port_map = PortMap({})
    # we try to keep pins together for each interface
    for component, iface in interfaces.items():
        for k, v in iface['interface']['members'].items():
            logger.debug(f"Interface {component}.{k}:")
            logger.debug(pformat(v))
            width = count_member_pins(k, v)
            logger.debug(f"  {k}: total {width} pins")
            old_ports = oldlock.port_map.get_ports(component, k) if oldlock else None
            if old_ports:
                logger.debug(f"  {component}.{k} found in pins.lock, reusing")
                logger.debug(pformat(old_ports))
                old_width = sum([len(p.pins) for p in old_ports.values()])
                if old_width != width:
                    raise ChipFlowError(
                        f"top level interface has changed size. "
                        f"Old size = {old_width}, new size = {width}"
                    )
                port_map.add_ports(component, k, old_ports)
            else:
                pins = package_type.allocate(unallocated, width)
                if len(pins) == 0:
                    raise ChipFlowError("No pins were allocated by {package}")
                logger.debug(f"allocated range: {pins}")
                unallocated = unallocated - set(pins)
                _map, _ = allocate_pins(k, v, pins)
                port_map.add_ports(component, k, _map)

    newlock = LockFile(process=process,
                       package=package,
                       port_map=port_map,
                       metadata=interfaces)

    with open(lockfile, 'w') as f:
        f.write(newlock.model_dump_json(indent=2, serialize_as_any=True))


class PinCommand:
    def __init__(self, config):
        self.config = config

    def build_cli_parser(self, parser):
        action_argument = parser.add_subparsers(dest="action")
        action_argument.add_parser(
            "lock", help=inspect.getdoc(self.lock).splitlines()[0])

    def run_cli(self, args):
        logger.debug(f"command {args}")
        if args.action == "lock":
            self.lock()

    def lock(self):
        """Lock the pin map for the design.

        Will attempt to reuse previous pin positions.
        """
        lock_pins()
