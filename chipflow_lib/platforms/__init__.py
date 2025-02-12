"""
Platform definititions
----------------------

This module defines the functionality you use in you code to target the ChipFlow platform

"""

from .silicon import *
from .sim import *
from .utils import *

__all__ = ['IO_ANNOTATION_SCHEMA', 'IOSignature', 'IOModel',
           'OutputIOSignature', 'InputIOSignature', 'BidirIOSignature',
           'load_pinlock', "PACKAGE_DEFINITIONS", 'top_components', 'LockFile',
           'Package', 'PortMap', 'Port', 'Process',
           'GAPackageDef', 'QuadPackageDef', 'BareDiePackageDef', 'BasePackageDef',
           'BringupPins', 'JTAGPins', 'PowerPins',
           'SiliconPlatformPort', 'SiliconPlatform',
           'SimPlatform']
