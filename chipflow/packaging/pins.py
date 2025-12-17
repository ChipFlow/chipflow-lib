# SPDX-License-Identifier: BSD-2-Clause
"""
Pin dataclasses and types for package definitions.

This module contains the fundamental building blocks for defining
physical pin assignments and power/signal groupings in IC packages.
"""

from dataclasses import dataclass, asdict
from enum import StrEnum, auto
from typing import Set, List, Union, Optional, TypeVar, Generic

from ..config import Voltage, VoltageRange


# Type aliases for pin collections
Pin = TypeVar('Pin')
PinSet = Set[Pin]
PinList = List[Pin]
Pins = Union[PinSet, PinList]


class PowerType(StrEnum):
    """Type of power pin (power or ground)"""
    POWER = auto()
    GROUND = auto()


class JTAGWire(StrEnum):
    """Wire names in a JTAG interface"""
    TRST = auto()
    TCK = auto()
    TMS = auto()
    TDI = auto()
    TDO = auto()


class PortType(StrEnum):
    """Type of port"""
    IO = auto()
    CLOCK = auto()
    RESET = auto()


@dataclass
class PowerPins(Generic[Pin]):
    """
    A matched pair of power pins, with optional notation of the voltage range.

    Attributes:
        power: The power (VDD) pin
        ground: The ground (VSS) pin
        voltage: Optional voltage range or specific voltage
        name: Optional name for this power domain
    """
    power: Pin
    ground: Pin
    voltage: Optional[VoltageRange | Voltage] = None
    name: Optional[str] = None

    def to_set(self) -> Set[Pin]:
        """Convert power pins to a set"""
        return set(asdict(self).values())


@dataclass
class JTAGPins(Generic[Pin]):
    """
    Pins for a JTAG interface.

    Attributes:
        trst: Test Reset pin
        tck: Test Clock pin
        tms: Test Mode Select pin
        tdi: Test Data In pin
        tdo: Test Data Out pin
    """
    trst: Pin
    tck: Pin
    tms: Pin
    tdi: Pin
    tdo: Pin

    def to_set(self) -> Set[Pin]:
        """Convert JTAG pins to a set"""
        return set(asdict(self).values())


@dataclass
class BringupPins(Generic[Pin]):
    """
    Essential pins for bringing up an IC, always in fixed locations.

    These pins are used for initial testing and debug of the IC.

    Attributes:
        core_power: List of core power pin pairs
        core_clock: Core clock input pin
        core_reset: Core reset input pin
        core_heartbeat: Heartbeat output pin (for liveness testing)
        core_jtag: Optional JTAG interface pins
    """
    core_power: List[PowerPins]
    core_clock: Pin
    core_reset: Pin
    core_heartbeat: Pin
    core_jtag: Optional[JTAGPins] = None

    def to_set(self) -> Set[Pin]:
        """Convert all bringup pins to a set"""
        jtag = self.core_jtag.to_set() if self.core_jtag else set()
        return {p for pp in self.core_power for p in asdict(pp).values()} | \
               set([self.core_clock, self.core_reset, self.core_heartbeat]) | \
               jtag
