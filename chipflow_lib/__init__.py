# SPDX-License-Identifier: BSD-2-Clause
from dataclasses import dataclass
from typing import Dict, Union, Any

from amaranth import (
        Module,
        Elaboratable,
        Signal,
        ClockDomain,
        ClockSignal,
        ResetSignal
        )

from amaranth.lib import io
from amaranth.lib.cdc import FFSynchronizer
from amaranth.lib.wiring import Component
from .platforms.iostream import PortSignature, IOShape

class ChipFlowError(Exception):
    pass

def make_hashable(cls):
    def __hash__(self):
        return hash(id(self))

    def __eq__(self, obj):
        return id(self) == id(obj)

    cls.__hash__ = __hash__
    cls.__eq__ = __eq__
    return cls


@make_hashable
@dataclass
class Heartbeat(Component):
    clock_domain: str = "sync"
    counter_size: int = 23
    name: str = "heartbeat"

    def pins():
        return IOShape({
            'heartbeat': {'heartbeat': ('o', 1)}
            })

    def __init__(self):
        super().__init__(PortSignature({}))
        self._ioshape = self.__class__.pins()
    
    def elaborate(self, platform):
        m = Module()
        # Heartbeat LED (to confirm clock/reset alive)
        heartbeat_ctr = Signal(self.counter_size)
        getattr(m.d, self.clock_domain).__iadd__(heartbeat_ctr.eq(heartbeat_ctr + 1))

        heartbeat_buffer = io.Buffer("o", self.ports.heartbeat)
        m.submodules.heartbeat_buffer = heartbeat_buffer
        m.d.comb += heartbeat_buffer.o.eq(heartbeat_ctr[-1])
        return m
