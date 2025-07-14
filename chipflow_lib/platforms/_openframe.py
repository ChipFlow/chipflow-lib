from typing import List, NamedTuple, Optional, Literal

from .utils import Voltage, PowerPins, LinearAllocPackageDef, BringupPins

class OFPin(NamedTuple):
    pin: int
    kind: str
    idx: int = 0
    voltage: Optional[Voltage] = None
    name: Optional[str] = None

OF_GPIO = [
    OFPin(31, "gpio", 0),  # gpio[31]
    OFPin(32, "gpio", 1),  # gpio[32]
    OFPin(33, "gpio", 2),  # gpio[33]
    OFPin(34, "gpio", 3),  # gpio[34]
    OFPin(35, "gpio", 4),  # gpio[35]
    OFPin(36, "gpio", 5),  # gpio[36]
    OFPin(37, "gpio", 6),  # gpio[37]
    OFPin(41, "gpio", 7),  # gpio[41]
    OFPin(42, "gpio", 8),  # gpio[42]
    OFPin(43, "gpio", 9),  # gpio[43]
    OFPin(44, "gpio", 10),  # gpio[44]
    OFPin(45, "gpio", 11),  # gpio[45]
    OFPin(46, "gpio", 12),  # gpio[46]
    OFPin(48, "gpio", 13),  # gpio[48]
    OFPin(50, "gpio", 14),  # gpio[50]
    OFPin(51, "gpio", 15),  # gpio[51]
    OFPin(53, "gpio", 16),  # gpio[53]
    OFPin(54, "gpio", 17),  # gpio[54]
    OFPin(55, "gpio", 18),  # gpio[55]
    OFPin(57, "gpio", 19),  # gpio[57]
    OFPin(58, "gpio", 20),  # gpio[58]
    OFPin(59, "gpio", 21),  # gpio[59]
    OFPin(60, "gpio", 22),  # gpio[60]
    OFPin(61, "gpio", 23),  # gpio[61]
    OFPin(62, "gpio", 24),  # gpio[62]
    OFPin(2, "gpio", 25),  # gpio[2]
    OFPin(3, "gpio", 26),  # gpio[3]
    OFPin(4, "gpio", 27),  # gpio[4]
    OFPin(5, "gpio", 28),  # gpio[5]
    OFPin(6, "gpio", 29),  # gpio[6]
    OFPin(7, "gpio", 30),  # gpio[7]
    OFPin(8, "gpio", 31),  # gpio[8]
    OFPin(11, "gpio", 32),  # gpio[11]
    OFPin(12, "gpio", 33),  # gpio[12]
    OFPin(13, "gpio", 34),  # gpio[13]
    OFPin(14, "gpio", 35),  # gpio[14]
    OFPin(15, "gpio", 36),  # gpio[15]
    OFPin(16, "gpio", 37),  # gpio[16]
    # OFPin(22, "gpio", 38) is assigned as clock
    # OFPin(24, "gpio", 39) is assigned as heartbeat
    OFPin(25, "gpio", 40),  # gpio[25]
    OFPin(26, "gpio", 41),  # gpio[26]
    OFPin(27, "gpio", 42),  # gpio[27]
    OFPin(28, "gpio", 43),  # gpio[28]
]

OF_CLOCK_PIN = OFPin(22, "gpio", 38)
OF_HEARTBEAT_PIN = OFPin(24, "gpio", 39)
OF_RESET_PIN = OFPin(21, "resetbi")

OF_CORE_POWER = [
    (OFPin(18,"vcc", voltage=1.8, name="d"),     # Power, Digital power supply
     OFPin(23,"vss", name="d")),                 # Digital power ground
]

OF_OTHER_POWER= [
    (OFPin(30,"vdd", voltage=3.3, name="a"),     # Power, Analog power supply
     OFPin(20,"vss", name="a")),                 # Analog power ground

    (OFPin(49,"vcc", voltage=1.8, name="d1"),    # Power, Digital power supply
     OFPin(39,"vss", name="d1")),                # Digital power ground

    (OFPin(17,"vdd", voltage=3.3, name="io"),    # Power, ESD and padframe power supply
     OFPin(29,"vss", name="io")),                # ESD and padframe ground

    (OFPin(64,"vdd", voltage=3.3, name="io"),    # Power, ESD and padframe power supply
     OFPin(56,"vss", name="io")),                # ESD and padframe ground

    (OFPin(63,"vcc", voltage=1.8, name="d2"),    # Power, Digital power supply
     OFPin(10,"vss", name="d2")),                # Digital power ground

    (OFPin(40,"vdd", voltage=3.3, name="a1"),    # Power,  Analog power supply
     OFPin(38,"vss", name="a1")),                # Analog power ground

    (OFPin(47,"vdd", voltage=3.3, name="a1"),    # Power,  Analog power supply
     OFPin(52,"vss", name="a1")),                # Analog power ground

    (OFPin(9,"vdd", voltage=3.3, name="a2"),     # Power,  Analog power supply
     OFPin(1,"vss", name="a2")),                 # Analog power ground
]

OF_OTHER = [
    OFPin(19, "NC")  # Not connected
]

class OpenframePackageDef(LinearAllocPackageDef):

    name: str = "Openframe"
    package_type: Literal["OpenframePackageDef"] = "OpenframePackageDef"
    def model_post_init(self, __context):
        self._ordered_pins = OF_GPIO

        super().model_post_init(__context)


    @property
    def _core_power(self) -> List[PowerPins]:
        pps = []

        for power, ground in OF_CORE_POWER:
            pp = PowerPins(power=power, ground=ground, voltage=power.voltage)
            pps.append(pp)

        return pps

    @property
    def bringup_pins(self) -> BringupPins:
        return BringupPins(
            core_power=self._core_power,
            core_clock=OF_CLOCK_PIN,
            core_reset=OF_RESET_PIN,
            core_heartbeat=OF_HEARTBEAT_PIN,
        )
