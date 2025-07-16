from enum import StrEnum, auto

class Sky130DriveMode(StrEnum):
    """
    Models the potential drive modes of an IO pad.
    Depending on process and cell library, these may be statically or dynamically configurable.

    You will get an error if the option is not available with the chosen process and cell library
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
