# SPDX-License-Identifier: BSD-2-Clause

from amaranth import *
from amaranth_boards.ulx3s import *
from amaranth.lib.cdc import ResetSynchronizer
from amaranth.lib import io, wiring
from amaranth.lib.wiring import In

from amaranth_soc import gpio

from amaranth_orchard.memory.spimemio import QSPIPins
from amaranth_orchard.io.uart import UARTPins
from amaranth_orchard.memory.hyperram import HyperRAMPins


class QSPIFlashProvider(Elaboratable):
    def __init__(self):
        self.pins = QSPIPins()

    def elaborate(self, platform):
        m = Module()

        flash = platform.request("spi_flash", dir=dict(cs='-', copi='-', cipo='-', wp='-', hold='-'))
        # Flash clock requires a special primitive to access in ECP5
        m.submodules.usrmclk = Instance(
            "USRMCLK",
            i_USRMCLKI=self.pins.clk_o,
            i_USRMCLKTS=ResetSignal(),  # tristate in reset for programmer accesss
            a_keep=1,
        )
        # IO pins and buffers
        m.submodules += Instance(
            "OBZ",
            o_O=flash.cs.io,
            i_I=self.pins.csn_o,
            i_T=ResetSignal(),
        )
        # Pins in order
        data_pins = ["copi", "cipo", "wp", "hold"]

        for i in range(4):
            m.submodules += Instance(
                "BB",
                io_B=getattr(flash, data_pins[i]).io,
                i_I=self.pins.d_o[i],
                i_T=~self.pins.d_oe[i],
                o_O=self.pins.d_i[i]
            )
        return m


class LEDGPIOProvider(wiring.Component):
    pins: In(gpio.PinSignature()).array(8)

    def elaborate(self, platform):
        m = Module()
        for i in range(8):
            led = io.Buffer("o", platform.request("led", i, dir="-"))
            m.submodules[f"led_{i}"] = led
            m.d.comb += led.o.eq(self.pins[i].o)
        return m


class ButtonGPIOProvider(wiring.Component):
    pins: In(gpio.PinSignature()).array(2)

    def elaborate(self, platform):
        m = Module()
        for i in range(2):
            btn = io.Buffer("i", platform.request("button_fire", i, dir="-"))
            m.submodules[f"btn_{i}"] = btn
            m.d.comb += self.pins[i].i.eq(btn.i)
        return m


class UARTProvider(Elaboratable):
    def __init__(self):
        self.pins = UARTPins()

    def elaborate(self, platform):
        m = Module()
        uart_pins = platform.request("uart", 0, dir=dict(rx="-", tx="-", rts="-", dtr="-"))
        m.submodules.uart_rx = uart_rx = io.Buffer("i", uart_pins.rx)
        m.submodules.uart_tx = uart_tx = io.Buffer("o", uart_pins.tx)
        m.d.comb += [
            uart_tx.o.eq(self.pins.tx_o),
            self.pins.rx_i.eq(uart_rx.i),
        ]
        return m


class HyperRAMProvider(Elaboratable):
    def __init__(self):
        self.pins = HyperRAMPins(cs_count=4)

    def elaborate(self, platform):
        # Dual HyperRAM PMOD, starting at GPIO 0+/-
        platform.add_resources([
            Resource(
                "hyperram",
                0,
                Subsignal("csn",    Pins("9- 9+ 10- 10+", conn=("gpio", 0), dir='o')),
                Subsignal("rstn",   Pins("8+", conn=("gpio", 0), dir='o')),
                Subsignal("clk",    Pins("8-", conn=("gpio", 0), dir='o')),
                Subsignal("rwds",   Pins("7+", conn=("gpio", 0), dir='io')),

                Subsignal("dq",     Pins("3- 2- 1- 0- 0+ 1+ 2+ 3+", conn=("gpio", 0), dir='io')),

                Attrs(IO_TYPE="LVCMOS33"),
            )
        ])

        hyperram = platform.request("hyperram", 0)

        m = Module()
        m.d.comb += [
            hyperram.clk.o.eq(self.pins.clk_o),
            hyperram.csn.o.eq(self.pins.csn_o),
            hyperram.rstn.o.eq(self.pins.rstn_o),

            hyperram.rwds.o.eq(self.pins.rwds_o),
            hyperram.rwds.oe.eq(self.pins.rwds_oe),
            self.pins.rwds_i.eq(hyperram.rwds.i),

            hyperram.dq.o.eq(self.pins.dq_o),
            hyperram.dq.oe.eq(self.pins.dq_oe),
            self.pins.dq_i.eq(hyperram.dq.i),
        ]
        return m


class JTAGProvider(Elaboratable):
    def __init__(self, cpu):
        pass

    def elaborate(self, platform):
        return Module()  # JTAG is not connected anywhere


class ClockResetProvider(Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        m = Module()
        m.submodules.clk25 = clk25 = io.Buffer("i", platform.request("clk25", dir="-"))
        m.d.comb += ClockSignal("sync").eq(clk25.i)
        m.submodules.btn_pwr = btn_pwr = io.Buffer("i", platform.request("button_pwr", dir="-"))
        m.submodules += ResetSynchronizer(btn_pwr.i, domain="sync")
        return m
