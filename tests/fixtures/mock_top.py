# SPDX-License-Identifier: BSD-2-Clause
from amaranth import Module
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

from chipflow_lib.platforms import InputIOSignature, OutputIOSignature, BidirIOSignature

__all__ = ["MockTop"]

TestSignature1 = wiring.Signature({
    "a": In(InputIOSignature(1)),
    "b": In(InputIOSignature(5)),
    "c": Out(OutputIOSignature(1)),
    "d": Out(OutputIOSignature(10)),
    "e": In(BidirIOSignature(1)),
    "f": In(BidirIOSignature(7)),
})

TestSignature2 = wiring.Signature({
    "a": Out(OutputIOSignature(1)),
    "b": Out(OutputIOSignature(5)),
    "c": In(InputIOSignature(1)),
    "d": In(InputIOSignature(10)),
    "e": Out(BidirIOSignature(1)),
    "f": Out(BidirIOSignature(7)),
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