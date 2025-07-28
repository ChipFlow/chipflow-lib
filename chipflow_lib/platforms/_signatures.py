# SPDX-License-Identifier: BSD-2-Clause

import re
from typing_extensions import Unpack, TypedDict

from amaranth.lib import wiring
from amaranth.lib.wiring import Out

from .. import ChipFlowError
from ._utils import InputIOSignature, OutputIOSignature, BidirIOSignature, IOModelOptions, _chipflow_schema_uri, amaranth_annotate

SIM_ANNOTATION_SCHEMA = str(_chipflow_schema_uri("sim-interface", 0))

class SimInterface(TypedDict):
    uid: str
    parameters: dict

_VALID_UID = re.compile('[a-zA-Z_.]').search

def sim_annotate(base="com.chipflow.chipflow_lib"):
    def decorate(klass):
        assert _VALID_UID(base)
        dec = amaranth_annotate(SimInterface, SIM_ANNOTATION_SCHEMA)
        klass = dec(klass)

        original_init = klass.__init__
        def new_init(self,*args, **kwargs):
            original_init(self, *args, **kwargs)
            self.__chipflow_annotation__ = {
                "uid": klass.__chipflow_uid__,
                "parameters": self.__chipflow_parameters__(),
                }

        klass.__init__ = new_init
        klass.__chipflow_uid__ = f"{base}.{klass.__name__}"
        klass.__chipflow_parameters__ = lambda self: {}
        return klass
    return decorate


@sim_annotate()
class JTAGSignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
        "trst": Out(InputIOSignature(1)),
        "tck": Out(InputIOSignature(1)),
        "tms": Out(InputIOSignature(1)),
        "tdi": Out(InputIOSignature(1)),
        "tdo": Out(OutputIOSignature(1)),
    })


@sim_annotate()
class SPISignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "sck": Out(OutputIOSignature(1)),
            "copi": Out(OutputIOSignature(1)),
            "cipo": Out(InputIOSignature(1)),
            "csn": Out(OutputIOSignature(1)),
        })

@sim_annotate()
class QSPIFlashSignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "clk": Out(OutputIOSignature(1)),
            "csn": Out(OutputIOSignature(1)),
            "d": Out(BidirIOSignature(4, individual_oe=True)),
        })

@sim_annotate()
class UARTSignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "tx": Out(OutputIOSignature(1)),
            "rx": Out(InputIOSignature(1)),
        })

@sim_annotate()
class I2CSignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
        "scl": Out(BidirIOSignature(1)),
        "sda": Out(BidirIOSignature(1))
    })

@sim_annotate()
class GPIOSignature(wiring.Signature):

    def __init__(self, pin_count=1, **kwargs: Unpack[IOModelOptions]):
        if pin_count > 32:
            raise ValueError(f"Pin pin_count must be lesser than or equal to 32, not {pin_count}")
        self._pin_count = pin_count
        kwargs['individual_oe'] = True
        super().__init__({
            "gpio": Out(BidirIOSignature(pin_count, **kwargs))
            })

    def __chipflow_parameters__(self):
        return {'pin_count': self._pin_count}

    def __repr__(self) -> str:
        return f"GPIOSignature(pin_count={self._pin_count}, {dict(self.members.items())})"


class SimulationCanLoadData:
    """
    Inherit from this in your object's Signature if you want a simulation model
    to be able to load data from your object
    """
    @classmethod
    def __init_submodule__(cls, /, *args, **kwargs):
        if wiring.Signature not in cls.mro():
            raise ChipFlowError("SimulationCanLoadData can only be used with ``wiring.Signature`` classes")
        original_annotations = getattr(cls, 'annotations')
        #def annotations(self, obj, /):
        #cls.annotate
