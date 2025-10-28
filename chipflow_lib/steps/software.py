# SPDX-License-Identifier: BSD-2-Clause
"""
Backward compatibility module for chipflow_lib.steps.software.

This module has been renamed to 'chipflow.steps.software'. This compatibility layer
will be maintained for some time but is deprecated. Please update your imports.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "The 'chipflow_lib.steps.software' module has been renamed to 'chipflow.steps.software'. "
    "Please update your imports to use 'chipflow.steps.software' instead. "
    "This compatibility shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export SoftwareStep (used by chipflow-examples)
from chipflow.steps.software import SoftwareStep  # noqa: F401
