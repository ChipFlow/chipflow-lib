# SPDX-License-Identifier: BSD-2-Clause
"""
Package definitions and pin allocation.

This module provides everything needed to define IC packages and
allocate pins to component interfaces, including:

- Pin dataclasses (PowerPins, JTAGPins, BringupPins)
- Port description models (PortDesc, PortMap)
- Lock file models (LockFile, Package)
- Base classes (BasePackageDef, LinearAllocPackageDef)
- Concrete package types (QuadPackageDef, BareDiePackageDef, GAPackageDef, OpenframePackageDef)
- Pin allocation algorithms
"""

# Pin types and dataclasses
from .pins import (
    Pin,
    PinSet,
    PinList,
    Pins,
    PowerType,
    JTAGWire,
    PortType,
    PowerPins,
    JTAGPins,
    BringupPins,
)

# Port description models
from .port_desc import (
    PortDesc,
    Interface,
    Component,
    PortMap,
)

# Lock file models
from .lockfile import (
    PackageDef,
    Package,
    LockFile,
)

# Base classes
from .base import (
    BasePackageDef,
    LinearAllocPackageDef,
)

# Concrete package types
from .standard import (
    BareDiePackageDef,
    QuadPackageDef,
)

from .grid_array import (
    GAPin,
    GALayout,
    GAPackageDef,
)

from .openframe import (
    OFPin,
    OpenframePackageDef,
)

# Allocation algorithms
from .allocation import (
    UnableToAllocate,
)

# Utility functions
from .utils import (
    load_pinlock,
    lock_pins,
)

# CLI commands
from .commands import (
    PinCommand,
)

# NOTE: This module is currently internal to the chipflow CLI.
# The public API will be designed in a future PR after working through
# real-world custom package examples.
# See: https://github.com/ChipFlow/chipflow-lib/issues/XXX
__all__ = [
    # Pin types
    'Pin',
    'PinSet',
    'PinList',
    'Pins',
    'PowerType',
    'JTAGWire',
    'PortType',
    'PowerPins',
    'JTAGPins',
    'BringupPins',
    # Port description
    'PortDesc',
    'Interface',
    'Component',
    'PortMap',
    # Lock file
    'PackageDef',
    'Package',
    'LockFile',
    # Base classes
    'BasePackageDef',
    'LinearAllocPackageDef',
    # Package types
    'BareDiePackageDef',
    'QuadPackageDef',
    'GAPin',
    'GALayout',
    'GAPackageDef',
    'OFPin',
    'OpenframePackageDef',
    # Allocation
    'UnableToAllocate',
    # Utilities
    'load_pinlock',
    'lock_pins',
    # CLI
    'PinCommand',
]
