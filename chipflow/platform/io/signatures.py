# SPDX-License-Identifier: BSD-2-Clause
"""
Common interface signatures for ChipFlow platforms.
"""

import re
import sys

from dataclasses import dataclass
from pathlib import Path
from typing import (
        List, Tuple, Any, Protocol, runtime_checkable,
        Literal, TypeVar, Generic, Annotated
        )

from typing_extensions import Unpack, TypedDict, NotRequired

from amaranth.lib import wiring
from amaranth.lib.wiring import Out
from pydantic import PlainSerializer, WithJsonSchema, WrapValidator

from ...utils import ensure_chipflow_root
from .iosignature import InputIOSignature, OutputIOSignature, BidirIOSignature, IOModelOptions, _chipflow_schema_uri
from .annotate import amaranth_annotate

SIM_ANNOTATION_SCHEMA = str(_chipflow_schema_uri("simulatable-interface", 0))
DATA_SCHEMA = str(_chipflow_schema_uri("simulatable-data", 0))
DRIVER_MODEL_SCHEMA = str(_chipflow_schema_uri("driver-model", 0))

class SimInterface(TypedDict):
    uid: str
    parameters: List[Tuple[str, Any]]

@runtime_checkable
@dataclass
class DataclassProtocol(Protocol):
    pass


@dataclass
class SoftwareBuild:
    """
    This holds the information needed for building software and providing the built outcome
    """

    sources: list[Path]
    includes: list[Path]
    include_dirs: list[Path]
    offset: int
    filename: Path
    build_dir: Path
    type: Literal["SoftwareBuild"] = "SoftwareBuild"

    def __init__(self, *, sources: list[Path], includes: list[Path] = [], include_dirs = [], offset=0):
        self.build_dir = ensure_chipflow_root() / 'build' / 'software'
        self.filename = self.build_dir / 'software.bin'
        self.sources= list(sources)
        self.includes = list(includes)
        self.include_dirs = list(include_dirs)
        self.offset = offset

@dataclass
class BinaryData:
    """
    This holds the information needed for building software and providing the built outcome
    """
    offset: int
    filename: Path
    build_dir: Path
    type: Literal["BinaryData"] = "BinaryData"

    def __init__(self, *, filename: Path, offset=0):
        self.build_dir = ensure_chipflow_root() / 'build' / 'software'
        if Path(filename).is_absolute():
            self.filename = filename
        else:
            self.filename = self.build_dir / filename
        self.offset = offset

_T_DataClass = TypeVar('_T_DataClass', bound=DataclassProtocol)
class Data(TypedDict, Generic[_T_DataClass]):
    data: _T_DataClass


class DriverModel(TypedDict):
    """
    Options for :class:`SoftwareDriverSignature`.

    Attributes:
        component: The ``wiring.Component`` that this is the signature for.
        regs_struct: The name of the C struct that represents the registers of this component.
        h_files: Header files for the driver.
        c_files: C files for the driver.
        regs_bus: The bus of this ``Component`` which contains its control registers.
        include_dirs: Any extra include directories needed by the driver.
    """
    # we just extrat the info we need, don't actually serialise a `wiring.Component`...
    component: Annotated[
                wiring.Component,
                PlainSerializer(lambda x: {
                    'name': x.__class__.__name__,
                    'file': sys.modules[x.__module__].__file__
                    }, return_type=dict),
                WithJsonSchema({
                    'type': 'object',
                    'properties': {
                        'name': { 'type': 'string' },
                        'file': { 'type': 'string' },
                        }
                    }),
                WrapValidator(lambda v, h: v)  # Don't care about it actually..
          ] | dict

    regs_struct: str
    h_files: NotRequired[list[Path]]
    c_files: NotRequired[list[Path]]
    include_dirs: NotRequired[list[Path]]
    regs_bus: NotRequired[str]
    _base_path: NotRequired[Path]  # gets filled by the decorator to the base directory where the Component was defined


_VALID_UID = re.compile('[a-zA-Z_.]').search

def _unpack_dict(d: dict) -> str:
    params = [ f"{k}={repr(v)}" for k,v in d.items()]
    return ', '.join(params)


def simulatable_interface(base="com.chipflow.chipflow"):
    """
    Decorator for creating simulatable interface signatures.

    The decorated class will have a ``__chipflow_parameters__`` method that returns
    a list of tuples (name, value). It is expected that a model that takes parameters
    is implemented as a template, with the parameters in the order given.

    Args:
        base: Base UID string for the interface (default: "com.chipflow.chipflow").

    Returns:
        A decorator function that adds chipflow annotation support to a class.
    """
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


def attach_data(external_interface: wiring.PureInterface, component: wiring.Component, data: DataclassProtocol):
    data_dict: Data = {'data':data}
    if component is not None:
        setattr(component.signature, '__chipflow_data__', data_dict)
        amaranth_annotate(Data, DATA_SCHEMA, '__chipflow_data__', decorate_object=True)(component.signature)
    setattr(external_interface.signature, '__chipflow_data__', data_dict)
    amaranth_annotate(Data, DATA_SCHEMA, '__chipflow_data__', decorate_object=True)(external_interface.signature)


class SoftwareDriverSignature(wiring.Signature):

    def __init__(self, members, **kwargs: Unpack[DriverModel]):
        definition_file = sys.modules[kwargs['component'].__module__].__file__
        assert definition_file
        base_path = Path(definition_file).parent.absolute()
        kwargs['_base_path'] = base_path
        if 'regs_bus' not in kwargs:
            kwargs['regs_bus'] = 'bus'

        # execute any generators here
        for k in ('c_files', 'h_files', 'includedirs'):
            if k in kwargs:
                kwargs[k] = list(kwargs[k])  #type: ignore

        self.__chipflow_driver_model__ = kwargs
        amaranth_annotate(DriverModel, DRIVER_MODEL_SCHEMA, '__chipflow_driver_model__', decorate_object=True)(self)
        super().__init__(members=members)
