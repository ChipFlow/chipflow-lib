"""
Platform definititions
----------------------

This module defines the functionality you use in you code to target the ChipFlow platform

"""

from .silicon import SiliconPlatformPort, SiliconPlatform
from .sim import SimPlatform
from .utils import (
        IO_ANNOTATION_SCHEMA, IOSignature, IOModel,
        OutputIOSignature, InputIOSignature, BidirIOSignature,
        )
from ._packages import PACKAGE_DEFINITIONS

__all__ = ['IO_ANNOTATION_SCHEMA', 'IOSignature', 'IOModel',
           'OutputIOSignature', 'InputIOSignature', 'BidirIOSignature',
           'SiliconPlatformPort', 'SiliconPlatform',
           'SimPlatform',
           'PACKAGE_DEFINITIONS']
