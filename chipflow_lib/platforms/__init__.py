"""
Platform definititions
----------------------

This module defines the functionality you use in you code to target the ChipFlow platform

"""

from .silicon import *
from .sim import *
from .utils import *

__all__ = ['PIN_ANNOTATION_SCHEMA', 'IOSignature',
           'OutputIOSignature', 'InputIOSignature', 'BidirIOSignature',
           'load_pinlock', "PACKAGE_DEFINITIONS", 'top_interfaces']
