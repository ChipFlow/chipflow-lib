"""
Platform definititions
----------------------

This module defines the functionality you use in you code to target the ChipFlow platform

"""

from .silicon import SiliconPlatformPort, SiliconPlatform
from .sim import SimPlatform
from ._utils import (
        IO_ANNOTATION_SCHEMA, IOSignature, IOModel, IOTripPoint, IOModelOptions,
        OutputIOSignature, InputIOSignature, BidirIOSignature,
        )
from ._packages import PACKAGE_DEFINITIONS
from ._sky130 import Sky130DriveMode

__all__ = ['IO_ANNOTATION_SCHEMA', 'IOSignature',
           'IOModel', 'IOModelOptions', 'IOTripPoint',
           'OutputIOSignature', 'InputIOSignature', 'BidirIOSignature',
           'SiliconPlatformPort', 'SiliconPlatform',
           'SimPlatform',
           'Sky130DriveMode',
           'PACKAGE_DEFINITIONS']
