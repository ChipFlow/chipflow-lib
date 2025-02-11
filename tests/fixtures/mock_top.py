# SPDX-License-Identifier: BSD-2-Clause
from amaranth import Module
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from chipflow_lib.platforms import InputPinSignature, OutputPinSignature, BidirPinSignature

__all__ = ["MockTop"]

TestSignature1 = wiring.Signature({
    "a": In(InputPinSignature(1)),
    "b": In(InputPinSignature(5)),
    "c": Out(OutputPinSignature(1)),
    "d": Out(OutputPinSignature(10)),
    "e": In(BidirPinSignature(1)),
    "f": In(BidirPinSignature(7)),
})

TestSignature2 = wiring.Signature({
    "a": Out(OutputPinSignature(1)),
    "b": Out(OutputPinSignature(5)),
    "c": In(InputPinSignature(1)),
    "d": In(InputPinSignature(10)),
    "e": Out(BidirPinSignature(1)),
    "f": Out(BidirPinSignature(7)),
})


# ---------

class MockTop(wiring.Component):
    def __init__(self):
        # Top level interfaces

        interfaces = {
            "test1" : Out(TestSignature1),
            "test2": Out(TestSignature2)
        }

        super().__init__(interfaces)

    def elaborate(self, platform):
        m = Module()
        for inpin, outpin in zip(self.test1.members, self.test2.members):
            m.d.comb += inpin.eq(outpin)
 
        return m