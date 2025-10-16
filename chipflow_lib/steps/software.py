"""
Backward compatibility shim for steps.software module.

This module re-exports software step functionality from the platform module.
New code should import directly from chipflow_lib.platform instead.
"""

# Re-export from platform module for backward compatibility
from ..platform import (  # noqa: F401
    SoftwareStep,
)
from ..platform.software import SoftwarePlatform  # noqa: F401

__all__ = [
    'SoftwareStep',
    'SoftwarePlatform',
]
