# SPDX-License-Identifier: BSD-2-Clause
"""
IO signatures and utilities for ChipFlow platforms.

This module provides IO signature definitions, annotations, and
platform-specific IO utilities.
"""

# IO signature definitions
from .iosignature import (
    IOTripPoint,
    IOModelOptions,
    IOModel,
    IO_ANNOTATION_SCHEMA,
    IOSignature,
    InputIOSignature,
    OutputIOSignature,
    BidirIOSignature,
    _chipflow_schema_uri,
)

# Interface signatures
from .signatures import (
    JTAGSignature,
    SPISignature,
    I2CSignature,
    UARTSignature,
    GPIOSignature,
    QSPIFlashSignature,
    attach_data,
    SoftwareDriverSignature,
    SoftwareBuild,
)

# Sky130-specific
from .sky130 import Sky130DriveMode

# Annotation utilities
from .annotate import amaranth_annotate, submodule_metadata

__all__ = [
    # IO Signatures
    'IOTripPoint',
    'IOModelOptions',
    'IOModel',
    'IO_ANNOTATION_SCHEMA',
    'IOSignature',
    'InputIOSignature',
    'OutputIOSignature',
    'BidirIOSignature',
    '_chipflow_schema_uri',
    # Interface Signatures
    'JTAGSignature',
    'SPISignature',
    'I2CSignature',
    'UARTSignature',
    'GPIOSignature',
    'QSPIFlashSignature',
    'attach_data',
    'SoftwareDriverSignature',
    'SoftwareBuild',
    # Sky130
    'Sky130DriveMode',
    # Annotations
    'amaranth_annotate',
    'submodule_metadata',
]
