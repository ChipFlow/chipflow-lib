"""
Platform definititions
----------------------

This module defines the functionality you use in you code to target the ChipFlow platform

"""

from .silicon import *
from .sim import *
from ._utils import (
        IO_ANNOTATION_SCHEMA, IOSignature, IOModel,
        OutputIOSignature, InputIOSignature, BidirIOSignature,
        PACKAGE_DEFINITIONS, Process,
        GAPackageDef, QuadPackageDef, BareDiePackageDef,
        BringupPins, JTAGPins, PowerPins
)

__all__ = ['IO_ANNOTATION_SCHEMA', 'IOSignature', 'IOModel',
           'OutputIOSignature', 'InputIOSignature', 'BidirIOSignature',
           'PACKAGE_DEFINITIONS', 'Process',
           'GAPackageDef', 'QuadPackageDef', 'BareDiePackageDef',
           'BringupPins', 'JTAGPins', 'PowerPins',
           'SiliconPlatformPort', 'SiliconPlatform',
           'SimPlatform']
