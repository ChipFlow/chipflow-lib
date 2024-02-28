# SPDX-License-Identifier: BSD-2-Clause

from amaranth import *
from amaranth.lib.cdc import FFSynchronizer

from amaranth_orchard.memory.spimemio import QSPIPins
from amaranth_orchard.base.gpio import GPIOPins
from amaranth_orchard.io.uart import UARTPins
from amaranth_orchard.memory.hyperram import HyperRAMPins


class QSPIFlashProvider(Elaboratable):
    def __init__(self):
        self.pins = QSPIPins()

    def elaborate(self, platform):
        m = Module()
        m.d.comb += [
            platform.request("flash_clk").o.eq(self.pins.clk_o),
            platform.request("flash_csn").o.eq(self.pins.csn_o),
        ]
        for index in range(4):
            pin = platform.request(f"flash_d{index}")
            m.d.comb += [
                self.pins.d_i[index].eq(pin.i),
                pin.o.eq(self.pins.d_o[index]),
                pin.oe.eq(self.pins.d_oe[index])
            ]
        return m


class LEDGPIOProvider(Elaboratable):
    def __init__(self):
        self.pins = GPIOPins(width=8)

    def elaborate(self, platform):
        m = Module()
        for index in range(8):
            pin = platform.request(f"gpio_{index}")
            m.d.comb += [
                self.pins.i[index].eq(pin.i),
                pin.o.eq(self.pins.o[index]),
                pin.oe.eq(self.pins.oe[index])
            ]
        return m


class ButtonGPIOProvider(Elaboratable):
    def __init__(self):
        self.pins = GPIOPins(width=2)

    def elaborate(self, platform):
        m = Module()
        for index in range(2):
            pin = platform.request(f"btn_{index}")
            m.d.comb += [
                self.pins.i[index].eq(pin.i),
                pin.o.eq(self.pins.o[index]),
                pin.oe.eq(self.pins.oe[index])
            ]
        return m


class UARTProvider(Elaboratable):
    def __init__(self):
        self.pins = UARTPins()

    def elaborate(self, platform):
        m = Module()
        m.d.comb += [
            platform.request("uart_tx").o.eq(self.pins.tx_o),
            self.pins.rx_i.eq(platform.request("uart_rx").i),
        ]
        return m


class HyperRAMProvider(Elaboratable):
    def __init__(self):
        self.pins = HyperRAMPins(cs_count=4)

    def elaborate(self, platform):
        m = Module()
        m.d.comb += [
            platform.request("ram_clk").o.eq(self.pins.clk_o),
            platform.request("ram_rstn").o.eq(self.pins.rstn_o),
        ]

        for index in range(4):
            platform.request(f"ram_csn_{index}").o.eq(self.pins.csn_o[index]),

        rwds = platform.request("ram_rwds")
        m.d.comb += [
            rwds.o.eq(self.pins.rwds_o),
            rwds.oe.eq(self.pins.rwds_oe),
            self.pins.rwds_i.eq(rwds.i),
        ]

        for index in range(8):
            dq = platform.request(f"ram_dq_{index}")
            m.d.comb += [
                dq.o.eq(self.pins.dq_o[index]),
                dq.oe.eq(self.pins.dq_oe[index]),
                self.pins.dq_i[index].eq(dq.i),
            ]

        return m


class JTAGProvider(Elaboratable):
    def __init__(self, cpu):
        self.cpu = cpu

    def elaborate(self, platform):
        m = Module()
        m.d.comb += [
            self.cpu.jtag_tck.eq(platform.request("jtag_tck").i),
            self.cpu.jtag_tdi.eq(platform.request("jtag_tdi").i),
            self.cpu.jtag_tms.eq(platform.request("jtag_tms").i),
            platform.request("jtag_tdo").o.eq(self.cpu.jtag_tdo),
        ]
        return m


class ClockResetProvider(Elaboratable):
    def elaborate(self, platform):
        m = Module()
        m.domains.sync = ClockDomain()
        m.d.comb += [
            ClockSignal().eq(platform.request("sys_clk").i),
        ]
        m.submodules.rst_sync = FFSynchronizer(
            ~platform.request("sys_rstn").i,
            ResetSignal())
        return m
