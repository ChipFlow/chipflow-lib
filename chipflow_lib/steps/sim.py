"""
Backward compatibility shim for steps.sim module.

This module re-exports sim step functionality from the platform module.
New code should import directly from chipflow_lib.platform instead.
"""

# Re-export from platform module for backward compatibility
from ..platform import (  # noqa: F401
    SimStep,
)
from ..platform.sim import SimPlatform  # noqa: F401

__all__ = [
    'SimStep',
    'SimPlatform',
]
