# SPDX-License-Identifier: BSD-2-Clause

from typing_extensions import Unpack, TypedDict

from amaranth.lib import wiring
from amaranth.lib.wiring import Out

from .platforms._utils import InputIOSignature, OutputIOSignature, BidirIOSignature, IOModelOptions, _chipflow_schema_uri, amaranth_annotate

SIM_ANNOTATION_SCHEMA = str(_chipflow_schema_uri("sim-interface", 0))

def sim_annotate(klass):
    class Model(TypedDict):
        sim_interface: str

    original_init_subclass = klass.__init_subclass__
    @classmethod
    def new_init_subclass(cls, /, **kwargs):
        if original_init_subclass:
            original_init_subclass(**kwargs)
        cls._model = {"sim_interface": cls.__name__}

    dec = amaranth_annotate(Model, SIM_ANNOTATION_SCHEMA)
    klass = dec(klass)
    klass.__init_subclass__ = new_init_subclass
    return klass


@sim_annotate
class SimulatableSignature(wiring.Signature):
    ...


SPISignature = SimulatableSignature({
    "sck": Out(OutputIOSignature(1)),
    "copi": Out(OutputIOSignature(1)),
    "cipo": Out(InputIOSignature(1)),
    "csn": Out(OutputIOSignature(1)),
})

UARTSignature = SimulatableSignature({
                "tx": Out(OutputIOSignature(1)),
                "rx": Out(InputIOSignature(1)),
            })

I2CSignature = SimulatableSignature({
    "scl": Out(BidirIOSignature(1)),
    "sda": Out(BidirIOSignature(1))
    })

class GPIOSignature(SimulatableSignature):
    def __init__(self, pin_count=1, **kwargs: Unpack[IOModelOptions]):
        if pin_count > 32:
            raise ValueError(f"Pin pin_count must be lesser than or equal to 32, not {pin_count}")
        self._pin_count = pin_count
        super().__init__({
            "gpio": Out(BidirIOSignature(pin_count, individual_oe=True, **kwargs))
            })
    def get_sim_parameters(self):
        return {'pin_count': self._pin_count}

    def __repr__(self) -> str:
        return f"GPIOSignature(pin_count={self._pin_count}, {dict(self.members.items())})"
