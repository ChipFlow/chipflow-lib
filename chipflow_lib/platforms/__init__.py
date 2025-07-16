"""
Platform definititions
----------------------

This module defines the functionality you use in you code to target the ChipFlow platform

"""

from .silicon import SiliconPlatformPort, SiliconPlatform
from .sim import SimPlatform
from ._utils import (
        IO_ANNOTATION_SCHEMA, IOSignature, IOModel, IODriveMode, IOTripPoint, IOModelOptions,
        OutputIOSignature, InputIOSignature, BidirIOSignature,
        )
from ._packages import PACKAGE_DEFINITIONS

__all__ = ['IO_ANNOTATION_SCHEMA', 'IOSignature',
           'IOModel', 'IOModelOptions', 'IODriveMode', 'IOTripPoint',
           'OutputIOSignature', 'InputIOSignature', 'BidirIOSignature',
           'SiliconPlatformPort', 'SiliconPlatform',
           'SimPlatform',
           'PACKAGE_DEFINITIONS']
