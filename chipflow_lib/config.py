# SPDX-License-Identifier: BSD-2-Clause
import os


import tomli
from pydantic import ValidationError

from . import ChipFlowError
from .config_models import Config

def get_dir_models():
    return os.path.dirname(__file__) + "/models"


def get_dir_software():
    return os.path.dirname(__file__) + "/software"


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


