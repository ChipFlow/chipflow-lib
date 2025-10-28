"""
Backward compatibility shim for steps.silicon module.

This module re-exports silicon step functionality from the platform module.
New code should import directly from chipflow.platform instead.
"""

# Re-export from platform module for backward compatibility
from ..platform import (  # noqa: F401
    SiliconStep,
)
from ..platform.silicon import SiliconPlatform  # noqa: F401
from ..utils import top_components  # noqa: F401

# Re-export dotenv for mocking in tests
import dotenv  # noqa: F401

__all__ = [
    'SiliconStep',
    'SiliconPlatform',
    'top_components',
    'dotenv',
]
