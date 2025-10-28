# SPDX-License-Identifier: BSD-2-Clause
"""
Backward compatibility module for chipflow_lib.

This module has been renamed to 'chipflow'. This compatibility layer
will be maintained for some time but is deprecated. Please update your
imports to use 'chipflow' instead of 'chipflow_lib'.

All functionality is re-exported from the chipflow module.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "The 'chipflow_lib' package has been renamed to 'chipflow'. "
    "Please update your imports to use 'chipflow' instead of 'chipflow_lib'. "
    "This compatibility shim will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export only the symbols actually used by chipflow-digital-ip and chipflow-examples
# Top-level exports (used by chipflow-examples)
from chipflow import ChipFlowError  # noqa: F401
from chipflow import __version__  # noqa: F401

# Internal API (used by tests and CLI)
from chipflow import _parse_config, _get_cls_by_reference, _ensure_chipflow_root, _get_src_loc  # noqa: F401

# Note: Submodule imports (chipflow_lib.platforms, chipflow_lib.steps, chipflow_lib.config)
# are handled by stub modules in their respective subdirectories
