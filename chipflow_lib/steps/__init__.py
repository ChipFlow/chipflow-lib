"""
Backward compatibility shim for steps module.

This module re-exports step functionality from the platform module.
New code should import directly from chipflow_lib.platform instead.

Steps provide an extensible way to modify the `chipflow` command behavior for a given design
"""

# Re-export from platform module for backward compatibility
from ..platform import (  # noqa: F401
    StepBase,
    setup_amaranth_tools,
    SiliconStep,
    SimStep,
    SoftwareStep,
    BoardStep,
)

from ..platform import IOSignature  # noqa: F401

__all__ = [
    'StepBase',
    'setup_amaranth_tools',
    'SiliconStep',
    'SimStep',
    'SoftwareStep',
    'BoardStep',
    'IOSignature',
]
