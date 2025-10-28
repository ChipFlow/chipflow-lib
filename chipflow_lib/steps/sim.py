# SPDX-License-Identifier: BSD-2-Clause
"""
Backward compatibility module for chipflow_lib.steps.sim.

This module has been renamed to 'chipflow.steps.sim'. This compatibility layer
will be maintained for some time but is deprecated. Please update your imports.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "The 'chipflow_lib.steps.sim' module has been renamed to 'chipflow.steps.sim'. "
    "Please update your imports to use 'chipflow.steps.sim' instead. "
    "This compatibility shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export SimStep (used by chipflow-examples)
from chipflow.steps.sim import SimStep  # noqa: F401
