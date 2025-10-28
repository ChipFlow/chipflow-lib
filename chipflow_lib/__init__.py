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

# Re-export everything from chipflow
from chipflow import *  # noqa: F401, F403
from chipflow import __version__, _parse_config, _get_cls_by_reference, _ensure_chipflow_root, _get_src_loc  # noqa: F401

# Maintain backward compatibility for submodules by making this a namespace package
# When someone imports chipflow_lib.something, Python will look for chipflow.something
__path__ = __import__('chipflow').__path__
