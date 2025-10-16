"""
Backward compatibility shim for platforms module.

This module re-exports platform functionality from the platform module.
New code should import directly from chipflow_lib.platform instead.

Platform definitions
--------------------

This module defines the functionality you use in your code to target the ChipFlow platform
"""

# Re-export from platform module for backward compatibility
from ..platform import (  # noqa: F401
    SiliconPlatformPort,
    SiliconPlatform,
    SimPlatform,
    SoftwarePlatform,
    IO_ANNOTATION_SCHEMA,
    IOSignature,
    IOModel,
    IOTripPoint,
    IOModelOptions,
    OutputIOSignature,
    InputIOSignature,
    BidirIOSignature,
    JTAGSignature,
    SPISignature,
    I2CSignature,
    UARTSignature,
    GPIOSignature,
    QSPIFlashSignature,
    attach_data,
    SoftwareDriverSignature,
    SoftwareBuild,
    Sky130DriveMode,
)

# Package definitions still live in platforms._packages
from ._packages import PACKAGE_DEFINITIONS  # noqa: F401

__all__ = [
    'IO_ANNOTATION_SCHEMA',
    'IOSignature',
    'IOModel',
    'IOModelOptions',
    'IOTripPoint',
    'OutputIOSignature',
    'InputIOSignature',
    'BidirIOSignature',
    'SiliconPlatformPort',
    'SiliconPlatform',
    'SimPlatform',
    'SoftwarePlatform',
    'JTAGSignature',
    'SPISignature',
    'I2CSignature',
    'UARTSignature',
    'GPIOSignature',
    'QSPIFlashSignature',
    'attach_data',
    'SoftwareDriverSignature',
    'SoftwareBuild',
    'Sky130DriveMode',
    'PACKAGE_DEFINITIONS',
]
