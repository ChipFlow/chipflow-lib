# SPDX-License-Identifier: BSD-2-Clause
"""
Platform definitions for ChipFlow.

This module provides platform implementations for silicon, simulation,
and software targets, along with their associated build steps.
"""

# Silicon platform
from .silicon import SiliconPlatformPort, SiliconPlatform
from .silicon_step import SiliconStep

# Simulation platform
from .sim import SimPlatform
from .sim_step import SimStep

# Software platform
from .software import SoftwarePlatform
from .software_step import SoftwareStep

# Board step
from .board_step import BoardStep

# IO signatures and utilities
from .io import (
    IO_ANNOTATION_SCHEMA, IOSignature, IOModel, IOTripPoint, IOModelOptions,
    OutputIOSignature, InputIOSignature, BidirIOSignature,
    JTAGSignature, SPISignature, I2CSignature, UARTSignature, GPIOSignature, QSPIFlashSignature,
    attach_data, SoftwareDriverSignature, SoftwareBuild,
    Sky130DriveMode,
)

# Base classes and utilities
from .base import StepBase, setup_amaranth_tools
from ..utils import top_components, get_software_builds

__all__ = [
    # Steps (primarily accessed via chipflow.steps.*)
    'SiliconStep',
    'SimStep',
    'SoftwareStep',
    'BoardStep',
    # Platforms
    'SimPlatform',
    'SiliconPlatform',
    'SiliconPlatformPort',
    'SoftwarePlatform',
    # Base classes
    'StepBase',
    # IO Signatures
    'IOSignature',
    'OutputIOSignature',
    'InputIOSignature',
    'BidirIOSignature',
    'JTAGSignature',
    'SPISignature',
    'I2CSignature',
    'UARTSignature',
    'GPIOSignature',
    'QSPIFlashSignature',
    # IO Configuration
    'IOModel',
    'IOModelOptions',
    'IOTripPoint',
    'Sky130DriveMode',
    # IO Utilities
    'attach_data',
    'SoftwareDriverSignature',
    'SoftwareBuild',
    # Utilities
    'setup_amaranth_tools',
    'top_components',
    'get_software_builds',
    # Schemas
    'IO_ANNOTATION_SCHEMA',
]
