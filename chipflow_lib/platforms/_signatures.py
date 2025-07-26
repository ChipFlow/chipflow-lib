# SPDX-License-Identifier: BSD-2-Clause

from typing_extensions import Unpack, TypedDict

from amaranth.lib import wiring
from amaranth.lib.wiring import Out

from ._utils import InputIOSignature, OutputIOSignature, BidirIOSignature, IOModelOptions, _chipflow_schema_uri, amaranth_annotate

SIM_ANNOTATION_SCHEMA = str(_chipflow_schema_uri("sim-interface", 0))

class SimInterface(TypedDict):
    name: str
    parameters: dict


def sim_annotate(klass):
    original_init_subclass = klass.__init_subclass__

    def new_init_subclass(cls, /, **kwargs):
        original_init = cls.__init__
        def new_init(self,*args, **kwargs):
            original_init(self, *args, **kwargs)
            self._model = {
                 "name": cls.__name__,
                 "parameters": self._get_sim_parameters(),
                 }

        if original_init_subclass:
            original_init_subclass(**kwargs)
        cls.__init__ = new_init

    dec = amaranth_annotate(SimInterface, SIM_ANNOTATION_SCHEMA)
    klass = dec(klass)
    klass.__init_subclass__ = classmethod(new_init_subclass)
    klass._get_sim_parameters = lambda self: {}
    return klass


@sim_annotate
class SimulatableSignature(wiring.Signature):
    ...

class JTAGSignature(SimulatableSignature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
        "trst": Out(InputIOSignature(1)),
        "tck": Out(InputIOSignature(1)),
        "tms": Out(InputIOSignature(1)),
        "tdi": Out(InputIOSignature(1)),
        "tdo": Out(OutputIOSignature(1)),
    })


class SPISignature(SimulatableSignature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "sck": Out(OutputIOSignature(1)),
            "copi": Out(OutputIOSignature(1)),
            "cipo": Out(InputIOSignature(1)),
            "csn": Out(OutputIOSignature(1)),
        })

class QSPIFlashSignature(SimulatableSignature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "clk": Out(OutputIOSignature(1)),
            "csn": Out(OutputIOSignature(1)),
            "d": Out(BidirIOSignature(4, individual_oe=True)),
        })

class UARTSignature(SimulatableSignature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "tx": Out(OutputIOSignature(1)),
            "rx": Out(InputIOSignature(1)),
        })

class I2CSignature(SimulatableSignature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
        "scl": Out(BidirIOSignature(1)),
        "sda": Out(BidirIOSignature(1))
    })

class GPIOSignature(SimulatableSignature):
    def __init__(self, pin_count=1, **kwargs: Unpack[IOModelOptions]):
        if pin_count > 32:
            raise ValueError(f"Pin pin_count must be lesser than or equal to 32, not {pin_count}")
        self._pin_count = pin_count
        kwargs['individual_oe'] = True
        super().__init__({
            "gpio": Out(BidirIOSignature(pin_count, **kwargs))
            })
    def _get_sim_parameters(self):
        return {'pin_count': self._pin_count}

    def __repr__(self) -> str:
        return f"GPIOSignature(pin_count={self._pin_count}, {dict(self.members.items())})"
