# SPDX-License-Identifier: BSD-2-Clause

from amaranth import *

from amaranth_orchard.memory.spimemio import QSPIPins
from amaranth_orchard.base.gpio import GPIOPins
from amaranth_orchard.io.uart import UARTPins
from amaranth_orchard.memory.hyperram import HyperRAMPins


class QSPIFlashProvider(Elaboratable):
    def __init__(self):
        self.pins = QSPIPins()

    def elaborate(self, platform):
        return platform.add_model("spiflash_model", self.pins, edge_det=['clk_o', 'csn_o'])


class LEDGPIOProvider(Elaboratable):
    def __init__(self):
        self.pins = GPIOPins(width=8)

    def elaborate(self, platform):
        return Module()


class ButtonGPIOProvider(Elaboratable):
    def __init__(self):
        self.pins = GPIOPins(width=2)

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.pins.i.eq(platform.buttons)
        return m


class UARTProvider(Elaboratable):
    def __init__(self):
        self.pins = UARTPins()

    def elaborate(self, platform):
        return platform.add_model("uart_model", self.pins, edge_det=[])


class HyperRAMProvider(Elaboratable):
    def __init__(self):
        self.pins = HyperRAMPins(cs_count=4)

    def elaborate(self, platform):
        return platform.add_model("hyperram_model", hram, edge_det=['clk_o'])


class JTAGProvider(Elaboratable):
    def __init__(self, cpu):
        pass

    def elaborate(self, platform):
        return Module()  # JTAG is not connected anywhere


class ClockResetProvider(Elaboratable):
    def elaborate(self, platform):
        m = Module()
        m.d.comb += ClockSignal("sync").eq(platform.clk)
        m.d.comb += ResetSignal("sync").eq(platform.rst)
        return m
