# SPDX-License-Identifier: BSD-2-Clause
"""
IO signature definitions for ChipFlow platforms.
"""

import logging
import pydantic

from collections.abc import Iterable
from typing import Tuple
from enum import StrEnum, auto
from typing import Annotated
from typing_extensions import TypedDict, Unpack, NotRequired

from amaranth.lib import wiring, io
from amaranth.lib.wiring import In, Out
from pydantic import ConfigDict, PlainSerializer

from .annotate import amaranth_annotate
from .sky130 import Sky130DriveMode

logger = logging.getLogger(__name__)


def _chipflow_schema_uri(name: str, version: int) -> str:
    return f"https://api.chipflow.com/schemas/{version}/{name}"


class IOTripPoint(StrEnum):
    """
    Models various options for trip points for inputs.
    Depending on process and cell library, these may be statically or dynamically configurable.

    You will get an error if the option is not available with the chosen process and cell library
    """

    # CMOS level switching (30%/70%) referenced to IO power domain
    CMOS = auto()
    # TTL level switching (low < 0.8v, high > 2.0v) referenced to IO power domain
    TTL = auto()
    # CMOS level switching referenced to core power domain (e.g. low power mode)
    VCORE = auto()
    # CMOS level switching referenced to external reference voltage (e.g. low power mode)
    VREF = auto()
    # Schmitt trigger
    SCHMITT_TRIGGER = auto()


IO_ANNOTATION_SCHEMA = str(_chipflow_schema_uri("pin-annotation", 0))


class IOModelOptions(TypedDict):
    """
    Options for an IO pad/pin.

    Attributes:
        invert: Polarity inversion. If the value is a simple :class:`bool`, it specifies inversion for
            the entire port. If the value is an iterable of :class:`bool`, the iterable must have the
            same length as the width of :py:`io`, and the inversion is specified for individual wires.
        individual_oe: controls whether each output wire is associated with an individual Output Enable bit
            or if a single OE bit will be used for entire port. The default value is False (indicating that a
            single OE bit controls the entire port).
        power_domain: The name of the I/O power domain. NB there is only one of these, so IO with multiple power domains must be split up.

        clock_domain: the name of the I/O's clock domain (see `Amaranth.ClockDomain`). NB there is only one of these, so IO with multiple clocks must be split up.
        buffer_in: Should the IO pad have an input buffer?
        buffer_out: Should the IO pad have an output buffer?
        sky130_drive_mode: Drive mode for output buffer on sky130
        trip_point: Trip Point configutation for input buffer
        init: The value for the initial values of the port
        init_oe: The value for the initial values of the output enable(s) of the port
    """

    invert: NotRequired[bool|Tuple[bool, ...]]
    individual_oe: NotRequired[bool]
    clock_domain: NotRequired[str]
    buffer_in: NotRequired[bool]
    buffer_out: NotRequired[bool]
    sky130_drive_mode: NotRequired[Sky130DriveMode]
    trip_point: NotRequired[IOTripPoint]
    init: NotRequired[int | bool]
    init_oe: NotRequired[int | bool]


@pydantic.config.with_config(ConfigDict(arbitrary_types_allowed=True))  # type: ignore[reportCallIssue]
class IOModel(IOModelOptions):
    """
    Setting for IO Ports (see also base class `IOModelOptions`)

    Attributes:
        direction: `io.Direction.Input`, `io.Direction.Output` or `io.Direction.Bidir`
        width: width of port, default is 1
    """

    width: int
    direction: Annotated[io.Direction, PlainSerializer(lambda x: x.value)]


@amaranth_annotate(IOModel, IO_ANNOTATION_SCHEMA, '_model')
class IOSignature(wiring.Signature):
    """An :py:obj:`Amaranth Signature <amaranth.lib.wiring.Signature>` used to decorate wires that would usually be brought out onto a port on the package.
    This class is generally not directly used.  Instead, you would typically utilize the more specific
    :py:obj:`InputIOSignature`, :py:obj:`OutputIOSignature`, or :py:obj:`BidirIOSignature` for defining pin interfaces.
    """

    def __init__(self, **kwargs: Unpack[IOModel]):
        # Special Handling for io.Direction, invert and clock_domain
        model = IOModel(**kwargs)
        assert 'width' in model
        assert 'direction' in model
        width = model['width']
        individual_oe = model['individual_oe'] if 'individual_oe' in model else False
        match model['direction']:
            case io.Direction.Bidir:
                sig = {
                    "o": Out(width),
                    "oe": Out(width if individual_oe else 1),
                    "i": In(width)
                }
            case io.Direction.Input:
                sig = {"i": In(width)}
            case io.Direction.Output:
                sig = {"o": Out(width)}
            case _:
                assert False
        if 'invert' in model:
            match model['invert']:
                case bool():
                    model['invert'] = (model['invert'],) * width
                case Iterable():
                    self._invert = tuple(model['invert'])
                    if len(self._invert) != width:
                        raise ValueError(f"Length of 'invert' ({len(self._invert)}) doesn't match "
                                         f"length of 'io' ({width})")
                case _:
                    raise TypeError(f"'invert' must be a bool or iterable of bool, not {model['invert']!r}")
        else:
            model['invert'] = (False,) * width

        if 'clock_domain' not in model:
            model['clock_domain'] = 'sync'

        self._model = model
        super().__init__(sig)

    @property
    def direction(self) -> io.Direction:
        "The direction of the IO port"
        return self._model['direction']

    @property
    def width(self) -> int:
        "The width of the IO port, in wires"
        return self._model['width']

    @property
    def invert(self) -> Iterable[bool]:
        "A tuple as wide as the IO port, with a bool for the polarity inversion for each wire"
        assert type(self._model['invert']) is tuple
        return self._model['invert']

    @property
    def options(self) -> IOModelOptions:
        """
        Options set on the io port at construction
        """
        return self._model

    def __repr__(self):
        return f"IOSignature({','.join('{0}={1!r}'.format(k,v) for k,v in self._model.items())})"


def OutputIOSignature(width: int, **kwargs: Unpack[IOModelOptions]):
    """This creates an :py:obj:`Amaranth Signature <amaranth.lib.wiring.Signature>` which is then used to decorate package output signals
    intended for connection to the physical pads of the integrated circuit package.

    :param width: specifies the number of individual output wires within this port, each of which will correspond to a separate physical pad on the integrated circuit package.
    """
    model: IOModel = kwargs | {'width': width, 'direction': io.Direction.Output}   # type: ignore[reportGeneralTypeIssues]
    return IOSignature(**model)


def InputIOSignature(width: int, **kwargs: Unpack[IOModelOptions]):
    """This creates an :py:obj:`Amaranth Signature <amaranth.lib.wiring.Signature>` which is then used to decorate package input signals
    intended for connection to the physical pads of the integrated circuit package.

    :param width: specifies the number of individual input wires within this port, each of which will correspond to a separate physical pad on the integrated circuit package.
    """

    model: IOModel = kwargs | {'width': width, 'direction': io.Direction.Input}   # type: ignore[reportGeneralTypeIssues]
    return IOSignature(**model)


def BidirIOSignature(width: int, **kwargs: Unpack[IOModelOptions]):
    """This creates an :py:obj:`Amaranth Signature <amaranth.lib.wiring.Signature>` which is then used to decorate package bi-directional signals
    intended for connection to the physical pads of the integrated circuit package.

    :param width: specifies the number of individual input/output wires within this port. Each pair of input/output wires will correspond to a separate physical pad on the integrated circuit package.
    """

    model: IOModel = kwargs | {'width': width, 'direction': io.Direction.Bidir}   # type: ignore[reportGeneralTypeIssues]
    return IOSignature(**model)
