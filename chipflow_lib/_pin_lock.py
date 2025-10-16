# SPDX-License-Identifier: BSD-2-Clause
"""
Backward compatibility shim for pin lock functionality.

This module re-exports pin lock functionality from the packaging module.
New code should import directly from chipflow_lib.packaging instead.
"""

# Re-export from packaging module for backward compatibility
from .packaging import lock_pins, PinCommand  # noqa: F401

__all__ = ['lock_pins', 'PinCommand']
