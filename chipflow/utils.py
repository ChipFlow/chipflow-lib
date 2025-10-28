# SPDX-License-Identifier: BSD-2-Clause
"""
Core utility functions for ChipFlow

This module provides core utilities used throughout the chipflow library.
"""

import importlib
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .config.models import Config
    from amaranth.lib import wiring


logger = logging.getLogger(__name__)


class ChipFlowError(Exception):
    """Base exception for ChipFlow errors"""
    pass


def get_cls_by_reference(reference: str, context: str):
    """
    Dynamically import and return a class by its module:class reference string.

    Args:
        reference: String in format "module.path:ClassName"
        context: Description of where this reference came from (for error messages)

    Returns:
        The class object

    Raises:
        ChipFlowError: If module or class cannot be found
    """
    logger.debug(f"get_cls_by_reference({reference}, {context}")
    module_ref, _, class_ref = reference.partition(":")
    try:
        module_obj = importlib.import_module(module_ref)
    except ModuleNotFoundError as e:
        logger.debug(f"import_module({module_ref}) caused {e}")
        raise ChipFlowError(
            f"Module `{module_ref}` was not found (referenced by {context} in [chipflow.top])"
        ) from e
    try:
        return getattr(module_obj, class_ref)
    except AttributeError as e:
        logger.debug(f"getattr({module_obj}, {class_ref}) caused {e}")
        raise ChipFlowError(
            f"Class `{class_ref}` not found in module `{module_ref}` "
            f"(referenced by {context} in [chipflow.top])"
        ) from e


def ensure_chipflow_root() -> Path:
    """
    Ensure CHIPFLOW_ROOT environment variable is set and return its path.

    If CHIPFLOW_ROOT is not set, sets it to the current working directory.
    Also ensures the root is in sys.path.

    Returns:
        Path to the chipflow root directory
    """
    # Check if we've already cached the root
    root = getattr(ensure_chipflow_root, 'root', None)
    if root:
        return root

    if "CHIPFLOW_ROOT" not in os.environ:
        logger.debug(
            f"CHIPFLOW_ROOT not found in environment. "
            f"Setting CHIPFLOW_ROOT to {os.getcwd()} for any child scripts"
        )
        os.environ["CHIPFLOW_ROOT"] = os.getcwd()
    else:
        logger.debug(f"CHIPFLOW_ROOT={os.environ['CHIPFLOW_ROOT']} found in environment")

    if os.environ["CHIPFLOW_ROOT"] not in sys.path:
        sys.path.append(os.environ["CHIPFLOW_ROOT"])

    # Cache the result
    ensure_chipflow_root.root = Path(os.environ["CHIPFLOW_ROOT"]).absolute()  # type: ignore
    return ensure_chipflow_root.root  # type: ignore


def get_src_loc(src_loc_at: int = 0):
    """
    Get the source location (filename, line number) of the caller.

    Args:
        src_loc_at: Number of frames to go back (0 = immediate caller)

    Returns:
        Tuple of (filename, line_number)
    """
    frame = sys._getframe(1 + src_loc_at)
    return (frame.f_code.co_filename, frame.f_lineno)


def compute_invert_mask(invert_list):
    """
    Compute a bit mask for signal inversion from a list of boolean invert flags.

    Args:
        invert_list: List of booleans indicating which bits should be inverted

    Returns:
        Integer mask where set bits indicate positions to invert
    """
    return sum(inv << bit for bit, inv in enumerate(invert_list))


def top_components(config: 'Config') -> Dict[str, 'wiring.Component']:
    """
    Return the top level components for the design, as configured in ``chipflow.toml``.

    Args:
        config: The parsed chipflow configuration

    Returns:
        Dictionary mapping component names to instantiated Component objects

    Raises:
        ChipFlowError: If component references are invalid or instantiation fails
    """
    from pprint import pformat

    component_configs = {}
    result = {}

    # First pass: collect component configs
    for name, conf in config.chipflow.top.items():
        if '.' in name:
            assert isinstance(conf, dict)
            param = name.split('.')[1]
            logger.debug(f"Config {param} = {conf} found for {name}")
            component_configs[param] = conf
        if name.startswith('_'):
            raise ChipFlowError(
                f"Top components cannot start with '_' character, "
                f"these are reserved for internal use: {name}"
            )

    # Second pass: instantiate components
    for name, ref in config.chipflow.top.items():
        if '.' not in name:  # Skip component configs, only process actual components
            cls = get_cls_by_reference(ref, context=f"top component: {name}")
            if name in component_configs:
                result[name] = cls(component_configs[name])
            else:
                result[name] = cls()
            logger.debug(
                f"Top members for {name}:\n"
                f"{pformat(result[name].metadata.origin.signature.members)}"
            )

    return result


def get_software_builds(m, component: str):
    """
    Extract software build information from a component's interfaces.

    Args:
        m: Module containing the component
        component: Name of the component

    Returns:
        Dictionary of interface names to SoftwareBuild objects
    """
    import pydantic

    # Import here to avoid circular dependency
    from .platform.io.signatures import DATA_SCHEMA, SoftwareBuild

    builds = {}
    iface = getattr(m.submodules, component).metadata.as_json()
    for interface, interface_desc in iface['interface']['members'].items():
        annotations = interface_desc['annotations']
        if DATA_SCHEMA in annotations and \
           annotations[DATA_SCHEMA]['data']['type'] == "SoftwareBuild":
            builds[interface] = pydantic.TypeAdapter(SoftwareBuild).validate_python(
                annotations[DATA_SCHEMA]['data']
            )
    return builds
