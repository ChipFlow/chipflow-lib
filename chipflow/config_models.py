# SPDX-License-Identifier: BSD-2-Clause
"""
Backward compatibility shim for config models.

This module re-exports configuration models from the config module.
New code should import directly from chipflow.config instead.
"""

# Re-export from config module for backward compatibility
from .config import (  # noqa: F401
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

__all__ = [
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
]
