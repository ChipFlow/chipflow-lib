# SPDX-License-Identifier: BSD-2-Clause
"""
Openframe package definition.

This module provides the package definition for the Efabless Openframe
carriage system, commonly used with open-source silicon projects.
"""

from typing import List, NamedTuple, Optional, Literal

from .base import LinearAllocPackageDef
from .pins import PowerPins, BringupPins
from ..config_models import Voltage


class OFPin(NamedTuple):
    """Pin identifier for Openframe package"""
    pin: int
    kind: str
    idx: int = 0
    voltage: Optional[Voltage] = None
    name: Optional[str] = None


# GPIO pins available for allocation
OF_GPIO = [
    OFPin(31, "gpio", 0),  # gpio[0]
    OFPin(32, "gpio", 1),  # gpio[1]
    OFPin(33, "gpio", 2),  # gpio[2]
    OFPin(34, "gpio", 3),  # gpio[3]
    OFPin(35, "gpio", 4),  # gpio[4]
    OFPin(36, "gpio", 5),  # gpio[5]
    OFPin(37, "gpio", 6),  # gpio[6]
    OFPin(41, "gpio", 7),  # gpio[7]
    OFPin(42, "gpio", 8),  # gpio[8]
    OFPin(43, "gpio", 9),  # gpio[9]
    OFPin(44, "gpio", 10),  # gpio[10]
    OFPin(45, "gpio", 11),  # gpio[11]
    OFPin(46, "gpio", 12),  # gpio[12]
    OFPin(48, "gpio", 13),  # gpio[13]
    OFPin(50, "gpio", 14),  # gpio[14]
    OFPin(51, "gpio", 15),  # gpio[15]
    OFPin(53, "gpio", 16),  # gpio[16]
    OFPin(54, "gpio", 17),  # gpio[17]
    OFPin(55, "gpio", 18),  # gpio[18]
    OFPin(57, "gpio", 19),  # gpio[19]
    OFPin(58, "gpio", 20),  # gpio[20]
    OFPin(59, "gpio", 21),  # gpio[21]
    OFPin(60, "gpio", 22),  # gpio[22]
    OFPin(61, "gpio", 23),  # gpio[23]
    OFPin(62, "gpio", 24),  # gpio[24]
    OFPin(2, "gpio", 25),  # gpio[25]
    OFPin(3, "gpio", 26),  # gpio[26]
    OFPin(4, "gpio", 27),  # gpio[27]
    OFPin(5, "gpio", 28),  # gpio[28]
    OFPin(6, "gpio", 29),  # gpio[29]
    OFPin(7, "gpio", 30),  # gpio[30]
    OFPin(8, "gpio", 31),  # gpio[31]
    OFPin(11, "gpio", 32),  # gpio[32]
    OFPin(12, "gpio", 33),  # gpio[33]
    OFPin(13, "gpio", 34),  # gpio[34]
    OFPin(14, "gpio", 35),  # gpio[35]
    OFPin(15, "gpio", 36),  # gpio[36]
    OFPin(16, "gpio", 37),  # gpio[37]
    # OFPin(22, "gpio", 38)   # gpio[38] is assigned as clock
    # OFPin(24, "gpio", 39)   # gpio[39] is assigned as heartbeat
    # OFPin(25, "gpio", 40),  # gpio[40] is assigned as reset
    OFPin(26, "gpio", 41),  # gpio[41]
    OFPin(27, "gpio", 42),  # gpio[42]
    OFPin(28, "gpio", 43),  # gpio[43]
]

# Fixed bringup pins
OF_CLOCK_PIN = OFPin(22, "gpio", 38)
OF_HEARTBEAT_PIN = OFPin(24, "gpio", 39)
OF_RESET_PIN = OFPin(25, "gpio", 40)

# Core power pins
OF_CORE_POWER = [
    (OFPin(18, "vcc", voltage=1.8, name="d"),  # Power, Digital power supply
     OFPin(23, "vss", name="d")),  # Digital power ground
]

# Additional power domains (analog, IO, etc.)
OF_OTHER_POWER = [
    (OFPin(30, "vdd", voltage=3.3, name="a"),  # Power, Analog power supply
     OFPin(20, "vss", name="a")),  # Analog power ground

    (OFPin(49, "vcc", voltage=1.8, name="d1"),  # Power, Digital power supply
     OFPin(39, "vss", name="d1")),  # Digital power ground

    (OFPin(17, "vdd", voltage=3.3, name="io"),  # Power, ESD and padframe power supply
     OFPin(29, "vss", name="io")),  # ESD and padframe ground

    (OFPin(64, "vdd", voltage=3.3, name="io"),  # Power, ESD and padframe power supply
     OFPin(56, "vss", name="io")),  # ESD and padframe ground

    (OFPin(63, "vcc", voltage=1.8, name="d2"),  # Power, Digital power supply
     OFPin(10, "vss", name="d2")),  # Digital power ground

    (OFPin(40, "vdd", voltage=3.3, name="a1"),  # Power, Analog power supply
     OFPin(38, "vss", name="a1")),  # Analog power ground

    (OFPin(47, "vdd", voltage=3.3, name="a1"),  # Power, Analog power supply
     OFPin(52, "vss", name="a1")),  # Analog power ground

    (OFPin(9, "vdd", voltage=3.3, name="a2"),  # Power, Analog power supply
     OFPin(1, "vss", name="a2")),  # Analog power ground
]

# Other pins
OF_OTHER = [
    OFPin(19, "NC")  # Not connected
]


class OpenframePackageDef(LinearAllocPackageDef):
    """
    Definition of the Efabless Openframe carriage package.

    This is a standardized package/carrier used for open-source
    silicon projects, particularly with the Efabless chipIgnite
    and OpenMPW programs.

    Attributes:
        name: Package name (default "openframe")
    """

    name: str = "openframe"
    package_type: Literal["OpenframePackageDef"] = "OpenframePackageDef"

    def model_post_init(self, __context):
        """Initialize pin ordering from GPIO list"""
        self._ordered_pins = OF_GPIO
        super().model_post_init(__context)

    @property
    def _core_power(self) -> List[PowerPins]:
        """Core power pin pairs"""
        pps = []
        for power, ground in OF_CORE_POWER:
            pp = PowerPins(power=power, ground=ground, voltage=power.voltage)
            pps.append(pp)
        return pps

    @property
    def bringup_pins(self) -> BringupPins:
        """Bringup pins for Openframe package"""
        return BringupPins(
            core_power=self._core_power,
            core_clock=OF_CLOCK_PIN,
            core_reset=OF_RESET_PIN,
            core_heartbeat=OF_HEARTBEAT_PIN,
        )
