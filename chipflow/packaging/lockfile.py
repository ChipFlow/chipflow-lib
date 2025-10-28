# SPDX-License-Identifier: BSD-2-Clause
"""
Lock file models for pin assignments.

The lock file captures the complete pin allocation for a design,
allowing pins to be locked and reused across design iterations.
"""

from typing import TYPE_CHECKING, Union

import pydantic

from .port_desc import PortMap

if TYPE_CHECKING:
    # Forward references to package definitions
    from .grid_array import GAPackageDef
    from .standard import QuadPackageDef, BareDiePackageDef
    from .openframe import OpenframePackageDef

# Import Process directly for pydantic to work properly
from ..config_models import Process


# Union of all package definition types
PackageDef = Union['GAPackageDef', 'QuadPackageDef', 'BareDiePackageDef', 'OpenframePackageDef']


class Package(pydantic.BaseModel):
    """
    Serializable identifier for a defined packaging option.

    Attributes:
        package_type: Package type (discriminated union of all PackageDef types)
    """
    package_type: PackageDef = pydantic.Field(discriminator="package_type")


class LockFile(pydantic.BaseModel):
    """
    Representation of a pin lock file.

    The lock file stores the complete pin allocation for a design,
    allowing pins to remain consistent across design iterations.

    Attributes:
        process: Semiconductor process being used
        package: Information about the physical package
        port_map: Mapping of components to interfaces to ports
        metadata: Amaranth metadata, for reference
    """
    process: Process  # Direct reference, not forward ref
    package: 'Package'
    port_map: PortMap
    metadata: dict
