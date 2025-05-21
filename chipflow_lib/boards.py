from dataclasses import dataclass
from typing import Dict, Optional, Callable

from amaranth import *
from amaranth.lib.build import Platform
from amaranth.lib.cdc import ResetSynchronizer
from amaranth.lib.wiring import connect, flipped, Signature, In, Out, Interface
from amaranth.build import Resource, Subsignal, Pins, Attrs

from amaranth_boards.ulx3s import (
    _ULX3SPlatform,
    ULX3S_12F_Platform,
    ULX3S_25F_Platform,
    ULX3S_45F_Platform,
    ULX3S_85F_Platform
    )


PortName = str
WiringFunc = Callable[[Module, Platform, PortName, Interface], None]
"""
A :py:WiringFunc declares a function that is used to wire an :py:`wiring.Interface` to a given named :py:`io.PortLike` on the given :py:`build.Platform`
"""

@dataclass
class BoardPrimitive:
    sig: Signature
    wire: WiringFunc

@dataclass
class BoardVariant:
    "Specification of an FPGA board"
    platform: type[Platform]
    "The :py:`type` of the :py:`build.Platform` to use for this board."
    reset_button: Optional[str] = None
    "Resource name to wire to reset"
    default_clock: Optional[str] = None
    "Default clock to use for this BoardVariant or BoardType"
    primitives: Optional[Dict[str, BoardPrimitive]] = None
    "A mapping of a Platform Resource name to the primitive that should be used to wire it up"

@dataclass
class BoardType(BoardVariant):
    variants: Dict[str, BoardVariant]
    "variants overlay the base BoardType"

def _wire_ulx3s_spi_flash(m: Module, platform: _ULX3SPlatform, port_name: str, flash: Interface) -> None:
        flash_port = platform.request("spi_flash", dir=dict(cs='-', copi='-', cipo='-', wp='-', hold='-'))
        # Flash clock requires a special primitive to access in ECP5
        m.submodules.usrmclk = Instance(
            "USRMCLK",
            i_USRMCLKI=flash.clk.o,
            i_USRMCLKTS=ResetSignal(),  # tristate in reset for programmer accesss
            a_keep=1,
        )

        # Flash IO buffers
        m.submodules += Instance(
            "OBZ",
            o_O=flash_port.cs.io,
            i_I=flash.csn.o,
            i_T=ResetSignal(),
        )

        # Connect flash data pins in order
        data_pins = ["copi", "cipo", "wp", "hold"]
        for i in range(4):
            m.submodules += Instance(
                "BB",
                io_B=getattr(flash_port, data_pins[i]).io,
                i_I=flash.d.o[i],
                i_T=~flash.d.oe[i],
                o_O=flash.d.i[i]
            )


_ulx3s_primitives = {
    'spi_flash': BoardPrimitive(
        interface_sig=Signature({
                "clk": Out(OutputPinSignature(1)),
                "csn": Out(OutputPinSignature(1)),
                "d": Out(BidirPinSignature(4, all_have_oe=True))
                }),
        wire=_wire_ulx3s_spi_flash)
    }

SUPPORTED_BOARDS = {
    'ULX3S': BoardType(
        platform=_ULX3SPlatform,
        reset_button='button_pwr',
        primitives=_ulx3s_primitives,
        variants={
            '12F': BoardVariant(platform=ULX3S_12F_Platform),
            '25F': BoardVariant(platform=ULX3S_25F_Platform),
            '45F': BoardVariant(platform=ULX3S_45F_Platform),
            '85F': BoardVariant(platform=ULX3S_85F_Platform),
            })
}

## Psudocode for board step:
#class _BoardWrapper:
#    def elaborate(self, platform):
#        m = Module()
#        top = top_interfaces()
#
#        board = SUPPORTED_BOARDS[self._board_type]
#        if self._board_variant:
#           board |= board.variants[self._board_variant]
#
#        m.domains += ClockDomain("sync")
#        m.d.comb += ClockSignal("sync").eq(platform.request().platform.default_clock)
#
#        btn_rst = platform.request(board.reset_button)
#        m.submodules.rst_sync = ResetSynchronizer(arst=btn_rst.i, domain="sync")
#
#        board_conf = config.chipflow.boards.{board_type}
#        board_conf |= config.chipflow.boards.{board_type}_{board_variant}
#
#        for (portname, interface) in config.chipflow.boards.{board_name}.items():
#            if portname in board.primitives:
#                check interface matches board.primitives[portname].sig
#                board.primitives[portname].wire(m, board.platform, portname, interface)
#            else:
#                iterate interface, wire up appropriatly to port with comb
#        return m
#
#class _BoardStep(BoardStep):
#    def __init__(self, config, target):
#        _setup_amaranth()
#        if target in config.chipflow.boards.keys():
#           platform = SUPPORTED_BOARDS[key].platform
#        # Also handle board variants,
#        self._board_type = target
#        self._board_variant = variant
#        super().__init__(config, platform)
#
#    def build(self):
#        self.platform.build(_BoardWrapper(self._board_type, self._board_variant), do_program=False)

