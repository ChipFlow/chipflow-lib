# SPDX-License-Identifier: BSD-2-Clause
import inspect
import logging

from pathlib import Path

from chipflow_lib import _parse_config, _ensure_chipflow_root
from chipflow_lib.platforms import top_components, LockFile, PACKAGE_DEFINITIONS

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


def lock_pins() -> None:
    # Get the config as dict for backward compatibility with top_components
    config_dict = _parse_config()

    # Parse with Pydantic for type checking and strong typing

    chipflow_root = _ensure_chipflow_root()
    lockfile = Path(chipflow_root, 'pins.lock')
    oldlock = None

    if lockfile.exists():
        oldlock = LockFile.model_validate_json(lockfile.read_text())

    print(f"Locking pins: {'using pins.lock' if lockfile.exists() else ''}")

    # Get package definition from dict instead of Pydantic model
    package_name = config_dict["chipflow"]["silicon"]["package"]
    package_def = PACKAGE_DEFINITIONS[package_name]
    process = config_dict["chipflow"]["silicon"]["process"]

    top = top_components(config_dict)

    # Use the PackageDef to allocate the pins:
    for name, component in top.items():
        package_def.register_component(name, component)

    newlock = package_def.allocate_pins(process, oldlock)

    with open(lockfile, 'w') as f:
        f.write(newlock.model_dump_json(indent=2, serialize_as_any=True))


class PinCommand:
    def __init__(self, config):
        self.config = config

    def build_cli_parser(self, parser):
        assert inspect.getdoc(self.lock) is not None
        action_argument = parser.add_subparsers(dest="action")
        action_argument.add_parser(
            "lock", help=inspect.getdoc(self.lock).splitlines()[0])  # type: ignore

    def run_cli(self, args):
        logger.debug(f"command {args}")
        if args.action == "lock":
            self.lock()

    def lock(self):
        """Lock the pin map for the design.

        Will attempt to reuse previous pin positions.
        """
        lock_pins()
