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
        except (pydantic.ValidationError, pydantic.PydanticUserError):
            raise ChipFlowError(
                "Lockfile `pins.lock` is misformed. "
                "Please remove and rerun `chipflow pin lock`"
            )

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
    from ..platforms._packages import PACKAGE_DEFINITIONS
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

    # Get package definition from dict
    package_name = config.chipflow.silicon.package
    package_def = PACKAGE_DEFINITIONS[package_name]
    process = config.chipflow.silicon.process

    top = top_components(config)

    # Use the PackageDef to allocate the pins:
    for name, component in top.items():
        package_def.register_component(name, component)

    newlock = package_def.allocate_pins(config, process, oldlock)

    with open(lockfile, 'w') as f:
        f.write(newlock.model_dump_json(indent=2, serialize_as_any=True))
