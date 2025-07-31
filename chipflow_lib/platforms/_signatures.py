# SPDX-License-Identifier: BSD-2-Clause

import re
import sys

from pathlib import Path
from typing import List, Tuple, Any
from typing_extensions import Unpack, TypedDict, NotRequired

from amaranth.lib import wiring
from amaranth.lib.wiring import Out

from ._utils import InputIOSignature, OutputIOSignature, BidirIOSignature, IOModelOptions, _chipflow_schema_uri
from ._annotate import amaranth_annotate

SIM_ANNOTATION_SCHEMA = str(_chipflow_schema_uri("simulatable-interface", 0))
SIM_DATA_SCHEMA = str(_chipflow_schema_uri("simulatable-data", 0))
DRIVER_MODEL_SCHEMA = str(_chipflow_schema_uri("driver-model", 0))

class SimInterface(TypedDict):
    uid: str
    parameters: List[Tuple[str, Any]]

class SimData(TypedDict):
    file_name: str
    offset: int

class DriverModel(TypedDict):
    """
    Options for @`driver_model` decorator

    Attributes:
        h_files: Header files for the driver
        c_files: C files for the driver
        busses: List of buses of this `Component` whos address range should be passed to the driver (defaults to ['bus'])
        include_dirs: any extra include directories needed by the driver
    """
    h_files: List[Path]
    c_files: NotRequired[List[Path]]
    include_dirs: NotRequired[List[Path]]
    busses: NotRequired[List[str]]
    _base_path: NotRequired[Path]  # gets filled by the decorator to the base directory where the Component was defined

_VALID_UID = re.compile('[a-zA-Z_.]').search

def _unpack_dict(d: dict) -> str:
    params = [ f"{k}={repr(v)}" for k,v in d.items()]
    return ', '.join(params)

"""
Attributes:
    __chipflow_parameters__: list of tuples (name, value).
        It is expected that a model that takes parameters is implmemted as a template, with the parameters in the order
        given.
"""
def simulatable_interface(base="com.chipflow.chipflow_lib"):
    def decorate(klass):
        assert _VALID_UID(base)
        dec = amaranth_annotate(SimInterface, SIM_ANNOTATION_SCHEMA)
        klass = dec(klass)

        def new_init(self,*args, **kwargs):
            original_init(self, *args, **kwargs)
            self.__chipflow_annotation__ = {
                "uid": klass.__chipflow_uid__,
                "parameters": self.__chipflow_parameters__(),
                }

        def repr(self) -> str:
            return f"{klass.__name__}({_unpack_dict(self.__chipflow_parameters__())}, {_unpack_dict(self._options)})"

        original_init = klass.__init__
        klass.__init__ = new_init
        klass.__chipflow_uid__ = f"{base}.{klass.__name__}"
        if not hasattr(klass, '__chipflow_parameters__'):
            klass.__chipflow_parameters__ = lambda self: []
        if not klass.__repr__:
            klass.__repr__ = repr
        return klass
    return decorate


@simulatable_interface()
class JTAGSignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
        "trst": Out(InputIOSignature(1)),
        "tck": Out(InputIOSignature(1)),
        "tms": Out(InputIOSignature(1)),
        "tdi": Out(InputIOSignature(1)),
        "tdo": Out(OutputIOSignature(1)),
    })


@simulatable_interface()
class SPISignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "sck": Out(OutputIOSignature(1)),
            "copi": Out(OutputIOSignature(1)),
            "cipo": Out(InputIOSignature(1)),
            "csn": Out(OutputIOSignature(1)),
        })

@simulatable_interface()
class QSPIFlashSignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "clk": Out(OutputIOSignature(1)),
            "csn": Out(OutputIOSignature(1)),
            "d": Out(BidirIOSignature(4, individual_oe=True)),
        })

@simulatable_interface()
class UARTSignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "tx": Out(OutputIOSignature(1)),
            "rx": Out(InputIOSignature(1)),
        })

@simulatable_interface()
class I2CSignature(wiring.Signature):
    def __init__(self, **kwargs: Unpack[IOModelOptions]):
        super().__init__({
            "scl": Out(BidirIOSignature(1)),
            "sda": Out(BidirIOSignature(1))
        })
        self._options = kwargs


@simulatable_interface()
class GPIOSignature(wiring.Signature):

    def __init__(self, pin_count=1, **kwargs: Unpack[IOModelOptions]):
        self._pin_count = pin_count
        self._options = kwargs
        kwargs['individual_oe'] = True
        super().__init__({
            "gpio": Out(BidirIOSignature(pin_count, **kwargs))
            })

    def __chipflow_parameters__(self):
        return [('pin_count',self._pin_count)]


def attach_simulation_data(c: wiring.Component, **kwargs: Unpack[SimData]):
    setattr(c.signature, '__chipflow_simulation_data__', kwargs)
    amaranth_annotate(SimData, SIM_DATA_SCHEMA, '__chipflow_simulation_data__', decorate_object=True)(c.signature)


def driver_model(**model: Unpack[DriverModel]):
    def decorate(klass):

        class_file = sys.modules[klass.__module__].__file__
        assert class_file

        model['_base_path'] = Path(class_file).parent.absolute()
        if 'busses' not in model:
            model['busses'] = ['bus']

        print(f"Decorating {klass}")
        original_init = klass.__init__
        def new_init(self,*args, **kwargs):

            print(f"Decorating {self} with driver_model({model})")
            original_init(self, *args, **kwargs)
            print(f"Ran original init")
            self.signature.__chipflow_driver_model__ = model

            amaranth_annotate(DriverModel, DRIVER_MODEL_SCHEMA, '__chipflow_driver_model__', decorate_object=True)(self.signature)

        klass.__init__ = new_init
        print(f" new init {klass.__init__} was {original_init}")
        return klass
    return decorate

