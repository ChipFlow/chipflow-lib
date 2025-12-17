# SPDX-License-Identifier: BSD-2-Clause
"""
Backward compatibility module for chipflow_lib.platforms.

This module has been renamed to 'chipflow.platform'. This compatibility layer
will be maintained for some time but is deprecated. Please update your imports.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "The 'chipflow_lib.platforms' module has been renamed to 'chipflow.platform'. "
    "Please update your imports to use 'chipflow.platform' instead. "
    "This compatibility shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export symbols used by chipflow-digital-ip and chipflow-examples
from chipflow.platform import (  # noqa: F401, E402
    # Pin signatures (used by both repos)
    BidirIOSignature,
    GPIOSignature,
    I2CSignature,
    InputIOSignature,
    JTAGSignature,
    OutputIOSignature,
    QSPIFlashSignature,
    SPISignature,
    UARTSignature,

    # Software driver support (used by both repos)
    SoftwareDriverSignature,

    # Platform-specific configuration (used by chipflow-examples)
    Sky130DriveMode,

    # Data attachment (used by chipflow-examples)
    attach_data,
    SoftwareBuild,
)

# Package definitions
from chipflow.packages import PACKAGE_DEFINITIONS  # noqa: F401, E402
