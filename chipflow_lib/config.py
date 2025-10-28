# SPDX-License-Identifier: BSD-2-Clause
"""
Backward compatibility module for chipflow_lib.config.

This module has been renamed to 'chipflow.config'. This compatibility layer
will be maintained for some time but is deprecated. Please update your imports.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "The 'chipflow_lib.config' module has been renamed to 'chipflow.config'. "
    "Please update your imports to use 'chipflow.config' instead. "
    "This compatibility shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export the entire config module (used by chipflow-examples via 'import chipflow_lib.config')
from chipflow import config as _config
import sys

# Make this module act as a proxy for chipflow.config
sys.modules[__name__] = _config
