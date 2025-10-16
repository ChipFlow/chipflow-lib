"""
Backward compatibility shim for platforms.silicon module.

This module re-exports silicon platform functionality from the platform module.
New code should import directly from chipflow_lib.platform instead.
"""

# Re-export from platform module for backward compatibility
from ..platform.silicon import (  # noqa: F401
    SiliconPlatform,
    SiliconPlatformPort,
    Sky130Port,
    port_for_process,
    IOBuffer,
    FFBuffer,
)

__all__ = [
    'SiliconPlatform',
    'SiliconPlatformPort',
    'Sky130Port',
    'port_for_process',
    'IOBuffer',
    'FFBuffer',
]
