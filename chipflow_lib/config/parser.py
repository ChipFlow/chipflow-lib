# SPDX-License-Identifier: BSD-2-Clause
"""
Configuration file parsing and utilities.
"""

import tomli

from pathlib import Path
from pydantic import ValidationError

from ..utils import ChipFlowError, ensure_chipflow_root
from .models import Config

def get_dir_models():
    return str(Path(__file__).parent / "models")


def get_dir_software():
    return str(Path(__file__).parent / "software")


def _parse_config_file(config_file) -> 'Config':
    """Parse a specific chipflow.toml configuration file."""

    with open(config_file, "rb") as f:
        config_dict = tomli.load(f)

    try:
        # Validate with Pydantic
        return Config.model_validate(config_dict)  # Just validate the config_dict
    except ValidationError as e:
        # Format Pydantic validation errors in a user-friendly way
        error_messages = []
        for error in e.errors():
            location = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"Error at '{location}': {message}")

        error_str = "\n".join(error_messages)
        raise ChipFlowError(f"Validation error in chipflow.toml:\n{error_str}")


def _parse_config() -> 'Config':
    """Parse the chipflow.toml configuration file."""
    chipflow_root = ensure_chipflow_root()
    config_file = Path(chipflow_root) / "chipflow.toml"
    try:
        return _parse_config_file(config_file)
    except FileNotFoundError:
        raise ChipFlowError(f"Config file not found. I expected to find it at {config_file}")
    except tomli.TOMLDecodeError as e:
        raise ChipFlowError(
            f"{config_file} has a formatting error: {e.msg} at line {e.lineno}, column {e.colno}"
        )
