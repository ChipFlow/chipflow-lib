# SPDX-License-Identifier: BSD-2-Clause
"""
Grid array package definitions.

This module provides package definitions for grid array packages
like BGA (Ball Grid Array) and PGA (Pin Grid Array) types.
"""

import logging
from enum import StrEnum, auto
from math import ceil, floor
from typing import Dict, List, Literal, NamedTuple, Optional, Set, Tuple, TYPE_CHECKING

from .base import BasePackageDef
from .pins import PowerPins, JTAGPins, BringupPins
from .lockfile import LockFile
from .allocation import _linear_allocate_components

if TYPE_CHECKING:
    from ..config_models import Config, Process

logger = logging.getLogger(__name__)


class GAPin(NamedTuple):
    """Pin identifier for grid array packages (row letter, column number)"""
    h: str  # Row (letter)
    w: int  # Column (number)

    def __lt__(self, other):
        if self.h == other.h:
            return self.w < other.w
        return self.h < other.h


class GALayout(StrEnum):
    """Layout type for grid array packages"""
    FULL = auto()  # Complete grid
    PERIMETER = auto()  # Only perimeter pins
    CHANNEL = auto()  # Top and bottom channels
    ISLAND = auto()  # Perimeter + center island


class GAPackageDef(BasePackageDef):
    """
    Definition of a grid array package.

    Pins or pads are arranged in a regular array of 'width' by 'height'.
    Pins are identified by a 2-tuple of (row, column), counting from
    the bottom left when looking at the underside of the package.
    Rows are identified by letter (A-Z), columns by number.

    The grid may be complete or have missing pins (e.g., center cutout).

    This includes many package types:

    - CPGA: Ceramic Pin Grid Array
    - OPGA: Organic Pin Grid Array
    - SPGA: Staggered Pin Grid Array
    - CABGA: Chip Array Ball Grid Array
    - CBGA/PBGA: Ceramic/Plastic Ball Grid Array
    - CTBGA: Thin Chip Array Ball Grid Array
    - CVBGA: Very Thin Chip Array Ball Grid Array
    - DSBGA: Die-Size Ball Grid Array
    - FBGA: Fine Ball Grid Array / Fine Pitch Ball Grid Array
    - FCmBGA: Flip Chip Molded Ball Grid Array
    - LBGA: Low-Profile Ball Grid Array
    - LFBGA: Low-Profile Fine-Pitch Ball Grid Array
    - MBGA: Micro Ball Grid Array
    - MCM-PBGA: Multi-Chip Module Plastic Ball Grid Array
    - nFBGA: New Fine Ball Grid Array
    - SuperBGA (SBGA): Super Ball Grid Array
    - TABGA: Tape Array BGA
    - TBGA: Thin BGA
    - TEPBGA: Thermally Enhanced Plastic Ball Grid Array
    - TFBGA: Thin and Fine Ball Grid Array
    - UFBGA/UBGA: Ultra Fine Ball Grid Array
    - VFBGA: Very Fine Pitch Ball Grid Array
    - WFBGA: Very Very Thin Profile Fine Pitch Ball Grid Array
    - wWLB: Embedded Wafer Level Ball Grid Array

    Attributes:
        width: Number of columns
        height: Number of rows
        layout_type: Pin layout configuration
        channel_width: For PERIMETER/CHANNEL/ISLAND layouts
        island_width: For ISLAND layout, size of center island
        missing_pins: Specific pins to exclude (overrides layout)
        additional_pins: Specific pins to add (overrides layout)
    """

    # Used by pydantic to differentiate when deserializing
    package_type: Literal["GAPackageDef"] = "GAPackageDef"

    width: int
    height: int
    layout_type: GALayout = GALayout.FULL
    channel_width: Optional[int] = None
    island_width: Optional[int] = None
    missing_pins: Optional[Set[GAPin]] = None
    additional_pins: Optional[Set[GAPin]] = None

    @staticmethod
    def _int_to_alpha(i: int):
        """
        Convert int to alpha representation (starting at 1).

        Skips letters that might be confused (I, N, O, Q, Z).
        """
        valid_letters = "ABCDEFGHJKLMPRSTUVWXY"
        out = ''
        while i > 0:
            char = i % len(valid_letters)
            i = i // len(valid_letters)
            out = valid_letters[char - 1] + out
        return out

    def _get_all_pins(self) -> Tuple[Set[GAPin], Set[GAPin] | None]:
        """
        Get all pins based on layout type.

        Returns:
            Tuple of (outer_pins, inner_pins) where inner_pins is
            only used for ISLAND layout
        """
        def pins_for_range(h1: int, h2: int, w1: int, w2: int) -> Set[GAPin]:
            pins = [GAPin(self._int_to_alpha(h), w) for h in range(h1, h2) for w in range(w1, w2)]
            return set(pins)

        match self.layout_type:
            case GALayout.FULL:
                pins = pins_for_range(1, self.height, 1, self.width)
                return (pins, None)

            case GALayout.PERIMETER:
                assert self.channel_width is not None
                pins = pins_for_range(1, self.height, 1, self.width) - \
                       pins_for_range(1 + self.channel_width, self.height - self.channel_width,
                                      1 + self.channel_width, self.width - self.channel_width)
                return (pins, None)

            case GALayout.ISLAND:
                assert self.channel_width is not None
                assert self.island_width is not None
                outer_pins = pins_for_range(1, self.height, 1, self.width) - \
                             pins_for_range(1 + self.channel_width, self.height - self.channel_width,
                                            1 + self.channel_width, self.width - self.channel_width)
                inner_pins = pins_for_range(
                    ceil(self.height / 2 - self.island_width / 2),
                    floor(self.height / 2 + self.island_width / 2),
                    ceil(self.width / 2 - self.island_width / 2),
                    floor(self.width / 2 + self.island_width / 2)
                )
                return (outer_pins, inner_pins)

            case GALayout.CHANNEL:
                assert self.channel_width is not None
                pins = pins_for_range(1, self.channel_width + 1, 1, self.width) | \
                       pins_for_range(self.height - self.channel_width, self.height, 1, self.width)
                return (pins, None)

    def model_post_init(self, __context):
        """Initialize pin ordering"""
        def sort_by_quadrant(pins: Set[GAPin]) -> List[GAPin]:
            """Sort pins by quadrant for better allocation"""
            quadrants: List[Set[GAPin]] = [set(), set(), set(), set()]
            midline_h = self._int_to_alpha(self.height // 2)
            midline_w = self.width // 2
            for pin in pins:
                if pin.h < midline_h and pin.w < midline_w:
                    quadrants[0].add(pin)
                if pin.h >= midline_h and pin.w < midline_w:
                    quadrants[1].add(pin)
                if pin.h < midline_h and pin.w >= midline_w:
                    quadrants[2].add(pin)
                if pin.h >= midline_h and pin.w >= midline_w:
                    quadrants[3].add(pin)
            ret = []
            for q in range(0, 3):
                ret.extend(sorted(quadrants[q]))
            return ret

        self._ordered_pins: List[GAPin] = []
        pins, _ = self._get_all_pins()
        pins -= self.bringup_pins.to_set()
        self._ordered_pins = sort_by_quadrant(pins)

        return super().model_post_init(__context)

    def allocate_pins(self, config: 'Config', process: 'Process', lockfile: LockFile | None) -> LockFile:
        """Allocate pins from the grid array"""
        portmap = _linear_allocate_components(
            self._interfaces,
            lockfile,
            self._allocate,
            set(self._ordered_pins)
        )
        bringup_pins = self._allocate_bringup(config)
        portmap.ports['_core'] = bringup_pins
        package = self._get_package()
        return LockFile(package=package, process=process, metadata=self._interfaces, port_map=portmap)

    def _allocate(self, available: Set[GAPin], width: int) -> List[GAPin]:
        """Allocate pins from available grid array pins"""
        from .allocation import _find_contiguous_sequence
        avail_n = sorted(available)
        logger.debug(f"GAPackageDef.allocate {width} from {len(avail_n)} remaining: {available}")
        ret = _find_contiguous_sequence(self._ordered_pins, avail_n, width)
        logger.debug(f"GAPackageDef.returned {ret}")
        assert len(ret) == width
        return ret

    @property
    def bringup_pins(self) -> BringupPins:
        """Bringup pins for grid array package"""
        return BringupPins(
            core_power=self._power,
            core_clock=GAPin('A', 2),
            core_reset=GAPin('A', 1),
            core_heartbeat=GAPin('A', 8),  # Output pin, after JTAG (A3-A7)
            core_jtag=self._jtag
        )

    @property
    def _power(self) -> List[PowerPins]:
        """
        Power pins for grid array package.

        Distributes power pins across the grid, with inner island
        (if present) dedicated to core power.
        """
        power_pins = []

        pins, inner = self._get_all_pins()

        # Allocate all of inner island to core pins, alternating
        try:
            if inner:
                it = iter(sorted(inner))
                for p in it:
                    power_pins.append(PowerPins(p, next(it)))
        except StopIteration:
            pass

        # Distribute the rest evenly
        try:
            it = iter(sorted(pins))
            for p in it:
                for name in ('', 'd'):
                    power_pins.append(PowerPins(p, next(it), name=name if name else None))
                # Skip 15 pins between power pin groups
                for i in range(0, 15):
                    next(it)
        except StopIteration:
            pass

        return power_pins

    @property
    def _jtag(self) -> JTAGPins:
        """JTAG pin map for the package"""
        # Default JTAG pin allocations
        # Use consecutive pins at the start of the package
        start_pin = 3
        return JTAGPins(
            trst=GAPin('A', start_pin),
            tck=GAPin('A', start_pin + 1),
            tms=GAPin('A', start_pin + 2),
            tdi=GAPin('A', start_pin + 3),
            tdo=GAPin('A', start_pin + 4)
        )

    @property
    def heartbeat(self) -> Dict[int, GAPin]:
        """Numbered set of heartbeat pins for the package"""
        # Default implementation with one heartbeat pin
        return {0: GAPin('A', 2)}
