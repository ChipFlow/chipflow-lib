# SPDX-License-Identifier: BSD-2-Clause
"""
Backward compatibility module for chipflow_lib.platforms.

This module has been renamed to 'chipflow.platforms'. This compatibility layer
will be maintained for some time but is deprecated. Please update your imports.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "The 'chipflow_lib.platforms' module has been renamed to 'chipflow.platforms'. "
    "Please update your imports to use 'chipflow.platforms' instead. "
    "This compatibility shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export symbols used by chipflow-digital-ip and chipflow-examples
from chipflow.platforms import (  # noqa: F401
    # Pin signatures (used by both repos)
    BidirIOSignature,
    GPIOSignature,
    I2CSignature,
    InputIOSignature,
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
