"""
Chipflow library
"""

import importlib.metadata
import logging
import os
import sys
import tomli
from pathlib import Path
from pydantic import ValidationError

__version__ = importlib.metadata.version("chipflow_lib")

logger = logging.getLogger(__name__)

class ChipFlowError(Exception):
    pass


def _get_cls_by_reference(reference, context):
    module_ref, _, class_ref = reference.partition(":")
    try:
        module_obj = importlib.import_module(module_ref)
    except ModuleNotFoundError as e:
        raise ChipFlowError(f"Module `{module_ref}` referenced by {context} is not found") from e
    try:
        return getattr(module_obj, class_ref)
    except AttributeError as e:
        raise ChipFlowError(f"Module `{module_ref}` referenced by {context} does not define "
                            f"`{class_ref}`") from e


def _ensure_chipflow_root():
    root = getattr(_ensure_chipflow_root, 'root', None)
    if root:
        return root

    if "CHIPFLOW_ROOT" not in os.environ:
        logger.debug(f"CHIPFLOW_ROOT not found in environment. Setting CHIPFLOW_ROOT to {os.getcwd()} for any child scripts")
        os.environ["CHIPFLOW_ROOT"] = os.getcwd()
    else:
        logger.debug(f"CHIPFLOW_ROOT={os.environ['CHIPFLOW_ROOT']} found in environment")

    if os.environ["CHIPFLOW_ROOT"] not in sys.path:
        sys.path.append(os.environ["CHIPFLOW_ROOT"])
    _ensure_chipflow_root.root = os.environ["CHIPFLOW_ROOT"]
    return _ensure_chipflow_root.root


def _parse_config():
    """Parse the chipflow.toml configuration file."""
    chipflow_root = _ensure_chipflow_root()
    config_file = Path(chipflow_root) / "chipflow.toml"
    try:
        return _parse_config_file(config_file)
    except FileNotFoundError:
       raise ChipFlowError(f"Config file not found. I expected to find it at {config_file}")
    except tomli.TOMLDecodeError as e:
        raise ChipFlowError(f"TOML Error found when loading {config_file}: {e.msg} at line {e.lineno}, column {e.colno}")


def _parse_config_file(config_file):
    """Parse a specific chipflow.toml configuration file."""
    from .config_models import Config

    with open(config_file, "rb") as f:
        config_dict = tomli.load(f)

    try:
        # Validate with Pydantic
        Config.model_validate(config_dict)  # Just validate the config_dict
        return config_dict  # Return the original dict for backward compatibility
    except ValidationError as e:
        # Format Pydantic validation errors in a user-friendly way
        error_messages = []
        for error in e.errors():
            location = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"Error at '{location}': {message}")

        error_str = "\n".join(error_messages)
        raise ChipFlowError(f"Validation error in chipflow.toml:\n{error_str}")
