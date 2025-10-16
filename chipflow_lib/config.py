# SPDX-License-Identifier: BSD-2-Clause
"""
Backward compatibility shim for config parsing.

This module re-exports config parsing utilities from the config module.
New code should import directly from chipflow_lib.config instead.
"""

# Re-export from config.parser module for backward compatibility
from .config.parser import (  # noqa: F401
    get_dir_models,
    get_dir_software,
    _parse_config_file,
)

__all__ = [
    'get_dir_models',
    'get_dir_software',
    '_parse_config_file',
]
