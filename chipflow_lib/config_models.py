# SPDX-License-Identifier: BSD-2-Clause
from typing import Dict, Optional, Any, List

from pydantic import BaseModel

from .platforms._internal import PACKAGE_DEFINITIONS, Process, Voltage


def known_package(package: str):
    if package not in PACKAGE_DEFINITIONS.keys():
        raise ValueError(f"{package} is not a valid package type. Valid package types are {PACKAGE_DEFINITIONS.keys()}")


class SiliconConfig(BaseModel):
    """Configuration for silicon in chipflow.toml."""
    process: 'Process'
    package: str
    power: Dict[str, Voltage] = {}
    debug: Optional[Dict[str, bool]] = None
    # This is still kept around to allow forcing pad locations.


class ChipFlowConfig(BaseModel):
    """Root configuration for chipflow.toml."""
    project_name: str
    top: Dict[str, Any] = {}
    steps: Optional[Dict[str, str]] = None
    silicon: Optional[SiliconConfig] = None
    clock_domains: Optional[List[str]] = None


class Config(BaseModel):
    """Root configuration model for chipflow.toml."""
    chipflow: ChipFlowConfig
