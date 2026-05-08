# SPDX-License-Identifier: BSD-2-Clause
"""
Utility functions for package and pin lock management.
"""

import logging
import pathlib
import pydantic

from pathlib import Path
from pprint import pformat
from typing import TYPE_CHECKING, Optional

from .. import ChipFlowError, ensure_chipflow_root, _parse_config
from .lockfile import LockFile

if TYPE_CHECKING:
    from ..config import Config

logger = logging.getLogger(__name__)


def load_pinlock() -> LockFile:
    """
    Load the pin lock file from the chipflow root.

    Returns:
        LockFile model

    Raises:
        ChipFlowError: If lockfile not found or malformed
    """
    chipflow_root = ensure_chipflow_root()
    lockfile = pathlib.Path(chipflow_root, 'pins.lock')
    if lockfile.exists():
        try:
            json = lockfile.read_text()
            return LockFile.model_validate_json(json)
        except (pydantic.ValidationError, pydantic.PydanticUserError) as e:
            raise ChipFlowError(
                "Lockfile `pins.lock` is misformed. "
                "Please remove and rerun `chipflow pin lock`"
            ) from e

    raise ChipFlowError("Lockfile `pins.lock` not found. Run `chipflow pin lock`")


def lock_pins(config: Optional['Config'] = None) -> None:
    """
    Create or update the pin lock file for the design.

    This allocates package pins to component interfaces and writes
    the allocation to pins.lock. Will attempt to reuse previous
    pin positions if pins.lock already exists.

    Args:
        config: Optional Config object. If not provided, will be parsed from chipflow.toml

    Raises:
        ChipFlowError: If configuration is invalid or pin allocation fails
    """
    # Import here to avoid circular dependency
    from ..packages import PACKAGE_DEFINITIONS
    from ..utils import top_components

    if config is None:
        config = _parse_config()

    chipflow_root = ensure_chipflow_root()
    lockfile = Path(chipflow_root, 'pins.lock')
    oldlock = None

    if lockfile.exists():
        print("Reusing current pin allocation from `pins.lock`")
        oldlock = LockFile.model_validate_json(lockfile.read_text())
    logger.debug(f"Old Lock =\n{pformat(oldlock)}")
    logger.debug(f"Locking pins: {'using pins.lock' if lockfile.exists() else ''}")

    if not config.chipflow.silicon:
        raise ChipFlowError("no [chipflow.silicon] section found in chipflow.toml")

    # Resolve the package definition. Most packages are fixed entries in
    # PACKAGE_DEFINITIONS (PGA144, BGA144, …). The special name "block"
    # is parameterized per project from [chipflow.silicon.block].
    package_name = config.chipflow.silicon.package
    if package_name == "block":
        from .standard import BlockPackageDef
        block_cfg = config.chipflow.silicon.block
        if block_cfg is None:
            raise ChipFlowError(
                'package = "block" requires a [chipflow.silicon.block] '
                'section with `width` and `height` (pin slot counts).'
            )
        package_def = BlockPackageDef(
            name="block",
            width=block_cfg.width,
            height=block_cfg.height,
        )
    else:
        if package_name not in PACKAGE_DEFINITIONS:
            raise ChipFlowError(
                f'Unknown package {package_name!r}. Known: '
                f'{sorted(PACKAGE_DEFINITIONS.keys()) + ["block"]}'
            )
        package_def = PACKAGE_DEFINITIONS[package_name]
    process = config.chipflow.silicon.process

    top = top_components(config)

    # Use the PackageDef to allocate the pins:
    for name, component in top.items():
        package_def.register_component(name, component)

    newlock = package_def.allocate_pins(config, process, oldlock)

    with open(lockfile, 'w') as f:
        f.write(newlock.model_dump_json(indent=2, serialize_as_any=True))


def swap_pins(pin_a: int, pin_b: int) -> None:
    """
    Swap two pin assignments in the current ``pins.lock``.

    Bringup pins (clock, reset, power, heartbeat, JTAG — everything
    under the ``_core`` component) are package-defined and cannot be
    swapped. Both inputs must currently be allocated to user ports of a
    package that uses integer pin numbers (Quad / Block / Openframe).

    Args:
        pin_a: First pin number.
        pin_b: Second pin number.

    Raises:
        ChipFlowError: ``pins.lock`` is missing or malformed; pins are
            identical; either pin is not allocated; either pin lives in
            the bringup ring; or the package uses non-integer pins.
    """
    if pin_a == pin_b:
        raise ChipFlowError(f"Cannot swap pin {pin_a} with itself.")

    chipflow_root = ensure_chipflow_root()
    lockfile_path = Path(chipflow_root, 'pins.lock')
    lockfile = load_pinlock()

    def find_slot(pin):
        for cname, comp in lockfile.port_map.ports.items():
            for iname, intf in comp.items():
                for pname, port in intf.items():
                    if port.pins is None:
                        continue
                    for i, p in enumerate(port.pins):
                        if not isinstance(p, int):
                            raise ChipFlowError(
                                "swap is currently only supported for "
                                "packages with integer pin numbers "
                                "(Quad / Block / Openframe). This "
                                f"lockfile uses pins of type "
                                f"{type(p).__name__}."
                            )
                        if p == pin:
                            return cname, iname, pname, i
        return None

    loc_a = find_slot(pin_a)
    loc_b = find_slot(pin_b)

    if loc_a is None:
        raise ChipFlowError(f"Pin {pin_a} is not allocated in pins.lock.")
    if loc_b is None:
        raise ChipFlowError(f"Pin {pin_b} is not allocated in pins.lock.")

    for loc, pin in ((loc_a, pin_a), (loc_b, pin_b)):
        if loc[0] == "_core":
            raise ChipFlowError(
                f"Pin {pin} is a bringup pin ({loc[1]}.{loc[2]}); "
                "bringup pins are package-defined and cannot be swapped."
            )

    ca, ia, na, idx_a = loc_a
    cb, ib, nb, idx_b = loc_b
    port_a = lockfile.port_map.ports[ca][ia][na]
    port_b = lockfile.port_map.ports[cb][ib][nb]
    assert port_a.pins is not None and port_b.pins is not None
    port_a.pins[idx_a] = pin_b
    port_b.pins[idx_b] = pin_a

    with open(lockfile_path, 'w') as f:
        f.write(lockfile.model_dump_json(indent=2, serialize_as_any=True))

    from .render import _slot_label
    label_a = _slot_label(ca, ia, na, idx_a, len(port_a.pins))
    label_b = _slot_label(cb, ib, nb, idx_b, len(port_b.pins))
    print(f"Swapped pin {pin_a} ({label_a}) with pin {pin_b} ({label_b}).")
