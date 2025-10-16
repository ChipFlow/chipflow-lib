# SPDX-License-Identifier: BSD-2-Clause
"""
Standard package definitions for common package types.

This module provides concrete package definitions for:
- Quad packages (QFN, LQFP, TQFP, etc.)
- Bare die packages
"""

import itertools
from enum import IntEnum
from typing import List, Literal, Tuple

from .base import LinearAllocPackageDef
from .pins import PowerPins, JTAGPins, BringupPins


class _Side(IntEnum):
    """Die sides for bare die packages"""
    N = 1
    E = 2
    S = 3
    W = 4

    def __str__(self):
        return f'{self.name}'


BareDiePin = Tuple[_Side, int]


class BareDiePackageDef(LinearAllocPackageDef):
    """
    Definition of a package with pins on four sides.

    Sides are labeled north, south, east, west with an integer
    identifier within each side, indicating pads across or down
    from top-left corner.

    This is typically used for direct die attach without traditional
    packaging.

    Attributes:
        width: Number of die pads on top and bottom sides
        height: Number of die pads on left and right sides
    """

    # Used by pydantic to differentiate when deserializing
    package_type: Literal["BareDiePackageDef"] = "BareDiePackageDef"

    width: int
    height: int

    def model_post_init(self, __context):
        """Initialize pin ordering"""
        pins = set(itertools.product((_Side.N, _Side.S), range(self.width)))
        pins |= set(itertools.product((_Side.W, _Side.E), range(self.height)))
        pins -= set(self.bringup_pins.to_set())

        self._ordered_pins: List[BareDiePin] = sorted(pins)
        return super().model_post_init(__context)

    @property
    def bringup_pins(self) -> BringupPins:
        """Bringup pins for bare die package"""
        # TODO: This makes no sense for anything that isn't tiny
        core_power = [
            PowerPins((_Side.N, 1), (_Side.N, 2)),
            PowerPins((_Side.W, 1), (_Side.W, 2), name='d')
        ]

        return BringupPins(
            core_power=core_power,
            core_clock=(_Side.N, 3),
            core_reset=(_Side.N, 3),
            core_heartbeat=(_Side.E, 1),
            core_jtag=JTAGPins(
                (_Side.E, 2),
                (_Side.E, 3),
                (_Side.E, 4),
                (_Side.E, 5),
                (_Side.E, 6)
            )
        )


class QuadPackageDef(LinearAllocPackageDef):
    """
    Definition of a quad flat package.

    A package with 'width' pins on the top and bottom and 'height'
    pins on the left and right. Pins are numbered anti-clockwise
    from the top left pin.

    This includes many common package types:

    - QFN: quad flat no-leads (bottom pad = substrate)
    - BQFP: bumpered quad flat package
    - BQFPH: bumpered quad flat package with heat spreader
    - CQFP: ceramic quad flat package
    - EQFP: plastic enhanced quad flat package
    - FQFP: fine pitch quad flat package
    - LQFP: low profile quad flat package
    - MQFP: metric quad flat package
    - NQFP: near chip-scale quad flat package
    - SQFP: small quad flat package
    - TQFP: thin quad flat package
    - VQFP: very small quad flat package
    - VTQFP: very thin quad flat package
    - TDFN: thin dual flat no-lead package
    - CERQUAD: low-cost CQFP

    Attributes:
        width: The number of pins across on the top and bottom edges
        height: The number of pins high on the left and right edges
    """

    # Used by pydantic to differentiate when deserializing
    package_type: Literal["QuadPackageDef"] = "QuadPackageDef"

    width: int
    height: int

    def model_post_init(self, __context):
        """Initialize pin ordering"""
        pins = set([i for i in range(1, self.width * 2 + self.height * 2)])
        pins -= set(self.bringup_pins.to_set())

        self._ordered_pins: List[int] = sorted(pins)
        return super().model_post_init(__context)

    @property
    def bringup_pins(self) -> BringupPins:
        """Bringup pins for quad package"""
        return BringupPins(
            core_power=self._power,
            core_clock=2,
            core_reset=1,
            core_heartbeat=self.width * 2 + self.height * 2 - 1,
            core_jtag=self._jtag
        )

    @property
    def _power(self) -> List[PowerPins]:
        """
        Power pins for a quad package.

        Power pins are always matched pairs in the middle of a side,
        with the number varying by package size. We don't move power
        pins from these locations to allow for easier bringup testing.

        Returns:
            List of PowerPins (core and IO power domains)
        """
        pins: List[PowerPins] = []
        # Heuristic for sensible number of power pins for given size
        n = (self.width + self.height) // 12

        # Left side (pins 1 to height)
        p = self.height // 2  # Middle of left side
        assert p > 3
        pins.append(PowerPins(p - 2, p - 1))
        pins.append(PowerPins(p, p + 1, name='d'))

        # Bottom side
        start = self.height
        if n > 2:
            p = start + self.width // 2
            pins.append(PowerPins(p - 2, p - 1))
            pins.append(PowerPins(p, p + 1, name='d'))

        # Right side
        start = start + self.width
        if n > 1:
            p = start + self.height // 2
            pins.append(PowerPins(p - 2, p - 1))
            pins.append(PowerPins(p, p + 1, name='d'))

        # Top side
        start = start + self.height
        if n > 3:
            p = start + self.width // 2
            pins.append(PowerPins(p - 2, p - 1))
            pins.append(PowerPins(p, p + 1, name='d'))

        return pins

    @property
    def _jtag(self) -> JTAGPins:
        """JTAG pin map for the package"""
        # Default JTAG pin allocations
        # Use consecutive pins at the start of the package
        start_pin = 2
        return JTAGPins(
            trst=start_pin,
            tck=start_pin + 1,
            tms=start_pin + 2,
            tdi=start_pin + 3,
            tdo=start_pin + 4
        )
