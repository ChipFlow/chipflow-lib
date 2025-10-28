# SPDX-License-Identifier: BSD-2-Clause
"""
Configuration management for ChipFlow.

This module provides configuration models and parsing functionality
for chipflow.toml configuration files.
"""

# Configuration models
from .models import (
    Process,
    Voltage,
    VoltageRange,
    SiliconConfig,
    SimulationConfig,
    CompilerConfig,
    SoftwareConfig,
    TestConfig,
    ChipFlowConfig,
    Config,
)

# Parsing utilities
from .parser import (
    get_dir_models,
    get_dir_software,
    _parse_config_file,
)

__all__ = [
    # Models (may be needed for type hints in user code)
    'Process',
    'Voltage',
    'VoltageRange',
    'SiliconConfig',
    'SimulationConfig',
    'CompilerConfig',
    'SoftwareConfig',
    'TestConfig',
    'ChipFlowConfig',
    'Config',
    # Public utilities
    'get_dir_models',
    'get_dir_software',
    '_parse_config_file',
]
