from enum import StrEnum, auto

# TODO describe how to access the port
class Sky130DriveMode(StrEnum):
    """
    Models the potential drive modes of an SkyWater 130 IO cell [sky130_fd_io__gpiov2](https://skywater-pdk.readthedocs.io/en/main/contents/libraries/sky130_fd_io/docs/user_guide.html)
    These are both statically configurable and can be set at runtime on the `:py:mod:drive_mode.Sky130Port` lines on the port.
    """
    # Strong pull-up, weak pull-down
    STRONG_UP_WEAK_DOWN = auto()
    # Weak pull-up, Strong pull-down
    WEAK_UP_STRONG_DOWN = auto()
    # Open drain with strong pull-down
    OPEN_DRAIN_STRONG_DOWN = auto()
    # Open drain-with strong pull-up
    OPEN_DRAIN_STRONG_UP= auto()
    # Strong pull-up, weak pull-down
    STRONG_UP_STRONG_DOWN = auto()
    # Weak pull-up, weak pull-down
    WEAK_UP_WEAK_DOWN = auto()
