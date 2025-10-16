# SPDX-License-Identifier: BSD-2-Clause
"""
Chipflow library

This is the main entry point for the ChipFlow library, providing tools for
building ASIC designs using the Amaranth HDL framework.
"""

import importlib.metadata
from typing import TYPE_CHECKING

# Import core utilities
from .utils import (
    ChipFlowError,
    ensure_chipflow_root,
    get_cls_by_reference,
    get_src_loc,
)

if TYPE_CHECKING:
    from .config import Config

__version__ = importlib.metadata.version("chipflow_lib")


# Maintain backward compatibility with underscore-prefixed names
_get_cls_by_reference = get_cls_by_reference
_ensure_chipflow_root = ensure_chipflow_root
_get_src_loc = get_src_loc


def _parse_config() -> 'Config':
    """Parse the chipflow.toml configuration file."""
    from .config.parser import _parse_config as config_parse
    return config_parse()


__all__ = [
    '__version__',
    'ChipFlowError',
    'ensure_chipflow_root',
]
