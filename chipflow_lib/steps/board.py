"""
Backward compatibility shim for steps.board module.

This module re-exports board step functionality from the platform module.
New code should import directly from chipflow_lib.platform instead.
"""

# Re-export from platform module for backward compatibility
from ..platform import (  # noqa: F401
    BoardStep,
)

__all__ = [
    'BoardStep',
]
