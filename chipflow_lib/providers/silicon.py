# SPDX-License-Identifier: BSD-2-Clause
from amaranth import *
from amaranth.build import *
from amaranth_boards.ulx3s import *
from amaranth_boards.ulx3s import *

from amaranth_orchard.memory.spimemio import QSPIPins
from amaranth_orchard.base.gpio import GPIOPins
from amaranth_orchard.io.uart import UARTPins
from amaranth_orchard.memory.hyperram import HyperRAMPins
from chipflow_lib.providers.base import BaseProvider


class QSPIFlash(BaseProvider):
    def add(self, m):
        flash = QSPIPins()
        m.d.comb += [
            self.platform.request("flash_clk").eq(flash.clk_o),
            self.platform.request("flash_csn").eq(flash.csn_o),
        ]
        for index in range(4):
            pin = self.platform.request(f"flash_d{index}")
            m.d.comb += [
                flash.d_i[index].eq(pin.i),
                pin.o.eq(flash.d_o[index]),
                pin.oe.eq(flash.d_oe[index])
            ]
        return flash


class LEDGPIO(BaseProvider):
    def add(self, m):
        leds = GPIOPins(width=8)
        for index in range(8):
            pin = self.platform.request(f"gpio_{index}")
            m.d.comb += [
                leds.i[index].eq(pin.i),
                pin.o.eq(leds.o[index]),
                pin.oe.eq(leds.oe[index])
            ]
        return leds


class ButtonGPIO(BaseProvider):
    def add(self, m):
        buttons = GPIOPins(width=2)
        for index in range(2):
            pin = self.platform.request(f"btn_{index}")
            m.d.comb += [
                buttons.i[index].eq(pin.i),
                pin.o.eq(buttons.o[index]),
                pin.oe.eq(buttons.oe[index])
            ]
        return buttons


class UART(BaseProvider):
    def add(self, m):
        uart = UARTPins()
        m.d.comb += [
            self.platform.request("uart_tx").o.eq(uart.tx_o),
            uart.rx_i.eq(self.platform.request("uart_rx")),
        ]
        return uart


class HyperRAM(BaseProvider):
    def add(self, m):
        # Dual HyperRAM PMOD, starting at GPIO 0+/-
        hram = HyperRAMPins(cs_count=4)

        # FIXME: update to use self.platform.request
        # self.platform.connect_io(m, hram, "ram")

        return hram


class JTAG(BaseProvider):
    def add(self, m, cpu):
        jtag_io = Record([
            ('tck_i', 1),
            ('tms_i', 1),
            ('tdi_i', 1),
            ('tdo_o', 1),
        ])
        m.d.comb += [
            cpu.jtag_tck.eq(self.platform.request("jtag_tck").i),
            cpu.jtag_tdi.eq(self.platform.request("jtag_tdi").i),
            cpu.jtag_tms.eq(self.platform.request("jtag_tms").i),
            self.platform.request("jtag_tdo").o.eq(cpu.jtag_tdo),
        ]
        return jtag_io


class Init(BaseProvider):
    def add(self, m):
        sys_io = Record([
            ('clk_i', 1),
            ('rstn_i', 1),
        ])
        m.d.comb += [
            sys_io.clk_i.eq(self.platform.request("sys_clk")),
            sys_io.rstn_i.eq(self.platform.request("sys_rstn")),
        ]
        m.domains.sync = ClockDomain()
        m.d.comb += ClockSignal().eq(sys_io.clk_i)

        rst = Signal()
        m.d.comb += rst.eq(~sys_io.rstn_i)
        rst_sync0 = Signal(reset_less=True)
        rst_sync1 = Signal(reset_less=True)
        m.d.sync += [
            rst_sync0.eq(rst),
            rst_sync1.eq(rst_sync0),
        ]
        m.d.comb += [
            ResetSignal().eq(rst_sync1),
        ]
