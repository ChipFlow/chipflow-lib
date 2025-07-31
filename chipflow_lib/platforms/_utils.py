import abc
import itertools
import logging
import pathlib
import pydantic

from collections import OrderedDict, deque
from collections.abc import Iterable
from pprint import pformat
from typing import Set, List, Dict, Optional, Union, Literal, Tuple

from dataclasses import dataclass, asdict
from enum import Enum, IntEnum, StrEnum, auto
from math import ceil, floor
from typing import (
    Any, Annotated, NamedTuple, Self, TYPE_CHECKING
)
from typing_extensions import (
    TypedDict, Unpack, NotRequired
)


from amaranth.lib import wiring, io
from amaranth.lib.wiring import In, Out
from pydantic import (
        ConfigDict, PlainSerializer,
        WrapValidator
        )


from .. import ChipFlowError, _ensure_chipflow_root, _get_cls_by_reference
from .._appresponse import AppResponseModel, OmitIfNone
from ._annotate import amaranth_annotate
from ._sky130 import Sky130DriveMode

if TYPE_CHECKING:
    from ..config_models import Config
    from ._openframe import OpenframePackageDef


logger = logging.getLogger(__name__)


def _chipflow_schema_uri(name: str, version: int) -> str:
    return f"https://api.chipflow.com/schemas/{version}/{name}"

Voltage = Annotated[
              float,
              PlainSerializer(lambda x: f'{x:.1e}V', return_type=str),
              WrapValidator(lambda v, h: h(v.strip('Vv ') if isinstance(v, str) else h(v)))
          ]


class VoltageRange(AppResponseModel):
    """
    Models a voltage range for a power domain or IO
    """
    min: Annotated[Optional[Voltage], OmitIfNone()] = None
    max: Annotated[Optional[Voltage], OmitIfNone()] = None
    typical: Annotated[Optional[Voltage], OmitIfNone()] = None


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


@pydantic.with_config(ConfigDict(arbitrary_types_allowed=True))  # type: ignore[reportCallIssue]
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


Pin = Union[Tuple[Any,...], str, int]
PinSet = Set[Pin]
PinList = List[Pin]
Pins = Union[PinSet, PinList]

class PowerType(StrEnum):
    POWER = auto()
    GROUND = auto()

class JTAGWire(StrEnum):
    TRST = auto()
    TCK = auto()
    TMS = auto()
    TDI = auto()
    TDO = auto()

JTAGSignature = wiring.Signature({
    JTAGWire.TRST: Out(InputIOSignature(1)),
    JTAGWire.TCK: Out(InputIOSignature(1)),
    JTAGWire.TMS: Out(InputIOSignature(1)),
    JTAGWire.TDI: Out(InputIOSignature(1)),
    JTAGWire.TDO: Out(OutputIOSignature(1)),
})

@dataclass
class PowerPins:
    "A matched pair of power pins, with optional notation of the voltage range"
    power: Pin
    ground: Pin
    voltage: Optional[VoltageRange | Voltage] = None
    name: Optional[str] = None
    def to_set(self) -> Set[Pin]:
        return set(asdict(self).values())

@dataclass
class JTAGPins:
    "Pins for a JTAG interface"
    trst: Pin
    tck: Pin
    tms: Pin
    tdi: Pin
    tdo: Pin

    def to_set(self) -> Set[Pin]:
        return set(asdict(self).values())

@dataclass
class BringupPins:
    core_power: List[PowerPins]
    core_clock: Pin
    core_reset: Pin
    core_heartbeat: Pin
    core_jtag: Optional[JTAGPins] = None

    def to_set(self) -> Set[Pin]:
        jtag = self.core_jtag.to_set() if self.core_jtag else set()
        return {p for pp in self.core_power for p in asdict(pp).values()} | \
               set([self.core_clock, self.core_reset, self.core_heartbeat]) | \
               jtag


class _Side(IntEnum):
    N = 1
    E = 2
    S = 3
    W = 4

    def __str__(self):
        return f'{self.name}'


class PortType(StrEnum):
    IO = auto()
    CLOCK = auto()
    RESET = auto()


class PortDesc(pydantic.BaseModel):
    type: str
    pins: List[Pin] | None  # None implies must be allocated at end
    port_name: str
    iomodel: IOModel

    @property
    def width(self):
        assert self.pins and 'width' in self.iomodel
        assert len(self.pins) == self.iomodel['width']
        return self.iomodel['width']

    @property
    def direction(self):
        assert 'direction' in self.iomodel
        return self.iomodel['direction']

    @property
    def invert(self) -> Iterable[bool] | None:
        if 'invert' in self.iomodel:
            if type(self.iomodel['invert']) is bool:
                return (self.iomodel['invert'],)
            else:
                return self.iomodel['invert']
        else:
            return None


def _group_consecutive_items(ordering: PinList, lst: PinList) -> OrderedDict[int, List[PinList]]:
    if not lst:
        return OrderedDict()

    grouped = []
    last = lst[0]
    current_group = [last]

    #logger.debug(f"_group_consecutive_items starting with {current_group}")

    for item in lst[1:]:
        idx = ordering.index(last)
        next = ordering[idx + 1] if idx < len(ordering) - 1 else None
        #logger.debug(f"inspecting {item}, index {idx}, next {next}")
        if item == next:
            current_group.append(item)
            #logger.debug("found consecutive, adding to current group")
        else:
            #logger.debug("found nonconsecutive, creating new group")
            grouped.append(current_group)
            current_group = [item]
        last = item

    grouped.append(current_group)
    d = OrderedDict()
    for g in grouped:
        # logger.debug(f"adding to group {len(g)} pins {g}")
        d.setdefault(len(g), []).append(g)
    return d


def _find_contiguous_sequence(ordering: PinList, lst: PinList, total: int) -> PinList:
    """Find the next sequence of n consecutive numbers in a sorted list

    Args:
        lst: Sorted list of numbers
        n: Length of consecutive sequence to find

    Returns:
        A slice indexing the first sequence of n consecutive numbers found within the given list
        if unable to find a consecutive list, allocate as contigously as possible
    """
    if not lst or len(lst) < total:
        raise ChipFlowError("Invalid request to find_contiguous_argument")

    grouped = _group_consecutive_items(ordering, lst)

    ret = []
    n = total

    # start with longest contiguous section, then continue into following sections
    keys = deque(grouped.keys())
    best = max(keys)
    start = keys.index(best)
    keys.rotate(start)

    for k in keys:
        for g in grouped[k]:
            assert n + len(ret) == total
            if k >= n:
                ret += g[0:min(n, k)]
                return ret
            else:
                n = n - k
                ret += g[0:k]

    return ret

def _count_member_pins(name: str, member: Dict[str, Any]) -> int:
    "Counts the pins from amaranth metadata"
    logger.debug(
        f"count_pins {name} {member['type']} "
        f"{member['annotations'] if 'annotations' in member else 'no annotations'}"
    )
    if member['type'] == 'interface' and 'annotations' in member \
       and IO_ANNOTATION_SCHEMA in member['annotations']:
        return member['annotations'][IO_ANNOTATION_SCHEMA]['width']
    elif member['type'] == 'interface':
        width = 0
        for n, v in member['members'].items():
            width += _count_member_pins('_'.join([name, n]), v)
        return width
    elif member['type'] == 'port':
        return member['width']
    return 0


def _allocate_pins(name: str, member: Dict[str, Any], pins: List[Pin], port_name: Optional[str] = None) -> Tuple[Dict[str, PortDesc], List[Pin]]:
    "Allocate pins based of Amaranth member metadata"

    if port_name is None:
        port_name = name

    pin_map = {}

    logger.debug(f"allocate_pins: name={name}, pins={pins}")
    logger.debug(f"member={pformat(member)}")

    if member['type'] == 'interface' and 'annotations' in member \
       and IO_ANNOTATION_SCHEMA in member['annotations']:
        model:IOModel = member['annotations'][IO_ANNOTATION_SCHEMA]
        logger.debug(f"matched IOSignature {model}")
        name = name
        width = model['width']
        pin_map[name] = PortDesc(pins=pins[0:width], type='io', port_name=port_name, iomodel=model)
        logger.debug(f"added '{name}':{pin_map[name]} to pin_map")
        return pin_map, pins[width:]
    elif member['type'] == 'interface':
        for k, v in member['members'].items():
            port_name = '_'.join([name, k])
            _map, pins = _allocate_pins(k, v, pins, port_name=port_name)
            pin_map |= _map
            logger.debug(f"{pin_map},{_map}")
        return pin_map, pins
    elif member['type'] == 'port':
        logger.warning(f"PortDesc '{name}' has no IOSignature, pin allocation likely to be wrong")
        width = member['width']
        model = IOModel(width=width, direction=io.Direction(member['dir']))
        pin_map[name] = PortDesc(pins=pins[0:width], type='io', port_name=port_name, iomodel=model)
        logger.debug(f"added '{name}':{pin_map[name]} to pin_map")
        return pin_map, pins[width:]
    else:
        logging.debug(f"Shouldnt get here. member = {member}")
        assert False


Interface = Dict[str, PortDesc]
Component = Dict[str, Interface]

class PortMap(pydantic.BaseModel):
    ports: Dict[str, Component] = {}

    def _add_port(self, component: str, interface: str, port_name: str, port: PortDesc):
        "Internally used by a `PackageDef`"
        if component not in self.ports:
            self.ports[component] = {}
        if interface not in self.ports[component]:
            self.ports[component][interface] = {}
        self.ports[component][interface][port_name] = port

    def _add_ports(self, component: str, interface: str, ports: Interface):
        "Internally used by a `PackageDef`"
        if component not in self.ports:
            self.ports[component] = {}
        self.ports[component][interface] = ports

    def get_ports(self, component: str, interface: str) -> Interface | None:

        "List the ports allocated in this PortMap for the given `Component` and `Interface`"
        if component not in self.ports or interface not in self.ports[component]:
            return None
        return self.ports[component][interface]

    def get_clocks(self) -> List[PortDesc]:
        ret = []
        for n, c in self.ports.items():
            for cn, i in c.items():
                for ni, p in i.items():
                    if p.type == "clock":
                        ret.append(p)
        return ret

    def get_resets(self) -> List[PortDesc]:
        ret = []
        for n, c in self.ports.items():
            for cn, i in c.items():
                for ni, p in i.items():
                    if p.type == "reset":
                        ret.append(p)
        return ret


class LockFile(pydantic.BaseModel):
    """
    Representation of a pin lock file.

    Attributes:
        package: Information about the physical package
        port_map: Mapping of components to interfaces to port
        metadata: Amaranth metadata, for reference
    """
    process: 'Process'
    package: 'Package'
    port_map: PortMap
    metadata: dict


PackageDef = Union['GAPackageDef', 'QuadPackageDef', 'BareDiePackageDef', 'OpenframePackageDef']

class Package(pydantic.BaseModel):
    """
    Serialisable identifier for a defined packaging option
    Attributes:
        package_type: Package type
    """
    package_type: PackageDef = pydantic.Field(discriminator="package_type")

# TODO: minimise names into more traditional form
def _linear_allocate_components(interfaces: dict, lockfile: LockFile | None, allocate, unallocated) -> PortMap:
    port_map = PortMap()
    for component, v in interfaces.items():
        for interface, v in v['interface']['members'].items():
            logger.debug(f"Interface {component}.{interface}:")
            logger.debug(pformat(v))
            width = _count_member_pins(interface, v)
            logger.debug(f"  {interface}: total {width} pins")
            old_ports = lockfile.port_map.get_ports(component, interface) if lockfile else None

            if old_ports:
                logger.debug(f"  {component}.{interface} found in pins.lock, reusing")
                logger.debug(pformat(old_ports))
                old_width = sum([len(p.pins) for p in old_ports.values() if p.pins is not None])
                if old_width != width:
                    raise ChipFlowError(
                        f"top level interface has changed size. "
                        f"Old size = {old_width}, new size = {width}"
                    )
                port_map._add_ports(component, interface, old_ports)
            else:
                pins = allocate(unallocated, width)
                if len(pins) == 0:
                    raise ChipFlowError("No pins were allocated")
                logger.debug(f"allocated range: {pins}")
                unallocated = unallocated - set(pins)
                _map, _ = _allocate_pins(f"{component}_{interface}", v, pins)
                port_map._add_ports(component, interface, _map)
    return port_map


class UnableToAllocate(ChipFlowError):
    pass


class BasePackageDef(pydantic.BaseModel, abc.ABC):
    """
    Abstract base class for the definition of a package
    Serialising this or any derived classes results in the
    description of the package
    Not serialisable!

    Attributes:
        name (str): The name of the package
        lockfile: Optional exisiting LockFile for the mapping

    """

    name: str

    def model_post_init(self, __context):
        self._interfaces: Dict[str, dict] = {}
        self._components: Dict[str, wiring.Component] = {}
        return super().model_post_init(__context)

    def register_component(self, name: str, component: wiring.Component) -> None:
        """
        Registers a port to be allocated to the pad ring and pins

        Args:
            component: Amaranth `wiring.Component` to allocate

        """
        self._components[name] = component
        self._interfaces[name] = component.metadata.as_json()

    def _get_package(self) -> Package:
        assert self is not Self
        return Package(package_type=self)  # type: ignore

    def _allocate_bringup(self, config: 'Config') -> Component:
        cds = set(config.chipflow.clock_domains) if config.chipflow.clock_domains else set()
        cds.discard('sync')

        d: Interface = { 'clk': PortDesc(type='clock',
                                          pins=[self.bringup_pins.core_clock],
                                          port_name='clk',
                                          iomodel=IOModel(width=1, direction=io.Direction.Input, clock_domain="sync")
                                      ),
                          'rst_n': PortDesc(type='reset',
                                           pins=[self.bringup_pins.core_reset],
                                           port_name='rst_n',
                                           iomodel=IOModel(width=1, direction=io.Direction.Input, clock_domain="sync",
                                                           invert=True)
                                      )
                       }
        assert config.chipflow.silicon
        if config.chipflow.silicon.debug and \
           config.chipflow.silicon.debug['heartbeat']:
            d['heartbeat'] = PortDesc(type='heartbeat',
                                  pins=[self.bringup_pins.core_heartbeat],
                                  port_name='heartbeat',
                                  iomodel=IOModel(width=1, direction=io.Direction.Output, clock_domain="sync")
                              )
        #TODO: JTAG
        return {'bringup_pins': d}

    @abc.abstractmethod
    def allocate_pins(self, config: 'Config', process: 'Process', lockfile: LockFile|None) -> LockFile:
        """
        Allocate package pins to the registered component.
        Pins should be allocated in the most usable way for *users* of the packaged IC.

        Returns: `LockFile` data structure represnting the allocation of interfaces to pins

        Raises:
            UnableToAllocate: Raised if the port was unable to be allocated.
        """
        ...

    @property
    def bringup_pins(self) -> BringupPins:
        """
        To aid bringup, these are always in the same place for each package type.
        Should include core power, clock and reset.

        Power, clocks and resets needed for non-core are allocated with the port.
        """
        ...

    def _sortpins(self, pins: Pins) -> PinList:
        return sorted(list(pins))


class LinearAllocPackageDef(BasePackageDef):
    """
    Base class for any package types where allocation is from a linear list of pins/pads
    Not serialisable

    To use, populate self._ordered_pins in model_post_init before calling super().model_post_init(__context).
    You will also likely need to override bringup_pins
    """
    def __init__(self, **kwargs):
        self._ordered_pins = None
        super().__init__(**kwargs)

    def allocate_pins(self, config: 'Config', process: 'Process', lockfile: LockFile|None) -> LockFile:
        assert self._ordered_pins
        portmap = _linear_allocate_components(self._interfaces, lockfile, self._allocate, set(self._ordered_pins))
        bringup_pins = self._allocate_bringup(config)
        portmap.ports['_core']=bringup_pins
        package = self._get_package()
        return LockFile(package=package, process=process, metadata=self._interfaces, port_map=portmap)

    def _allocate(self, available: Set[int], width: int) -> List[Pin]:
        assert self._ordered_pins
        avail_n: List[Pin] = sorted(available)
        ret = _find_contiguous_sequence(self._ordered_pins, avail_n, width)
        assert len(ret) == width
        return ret


class BareDiePackageDef(LinearAllocPackageDef):
    """
    Definition of a package with pins on four sides, labelled north, south, east, west
    with an integer identifier within each side, indicating pads across or down from top-left corner

    Attributes:
        width (int): Number of die pads on top and bottom sides
        height (int): Number of die pads on left and right sides
    """

    # Used by pydantic to differentate when deserialising
    package_type: Literal["BareDiePackageDef"] = "BareDiePackageDef"

    width: int
    height: int

    def model_post_init(self, __context):
        pins = set(itertools.product((_Side.N, _Side.S), range(self.width)))
        pins |= set(itertools.product((_Side.W, _Side.E), range(self.height)))
        pins -= set(self.bringup_pins.to_set())

        self._ordered_pins: List[Pin] = sorted(pins)
        return super().model_post_init(__context)

    @property
    def bringup_pins(self) -> BringupPins:
        core_power = PowerPins(
            (_Side.N, 1),
            (_Side.N, 2)
        )
        return BringupPins(
            core_power=[core_power],
            core_clock=(_Side.N, 3),
            core_reset=(_Side.N, 3),
            core_heartbeat=(_Side.E, 1),
            core_jtag=JTAGPins(
                (_Side.E, 2),
                (_Side.E, 3),
                (_Side.E, 4),
                (_Side.E, 5),
                (_Side.E, 6)
            )
        )


class QuadPackageDef(LinearAllocPackageDef):
    """
    Definiton of a package a row of 'width* pins on the top and bottom of the package and 'height' pins
    on the left and right

    The pins are numbered anti-clockwise from the top left hand pin.

    This includes the following types of package:
    .. csv-table:
    :header: "Package", "Description"
    "QFN", "quad flat no-leads package. It's assumed the bottom pad is connected to substrate."
    "BQFP", "bumpered quad flat package"
    "BQFPH", "bumpered quad flat package with heat spreader"
    "CQFP", "ceramic quad flat package"
    "EQFP", "plastic enhanced quad flat package"
    "FQFP", "fine pitch quad flat package"
    "LQFP", "low profile quad flat package"
    "MQFP", "metric quad flat package"
    "NQFP", "near chip-scale quad flat package."
    "SQFP", "small quad flat package"
    "TQFP", "thin quad flat package"
    "VQFP", "very small quad flat package"
    "VTQFP", "very thin quad flat package"
    "TDFN", "thin dual flat no-lead package."
    "CERQUAD", "low-cost CQFP"

    Attributes:
        width: The number of pins across on the top and bottom edges
        hight: The number of pins high on the left and right edges
    """

    # Used by pydantic to differentate when deserialising
    package_type: Literal["QuadPackageDef"] = "QuadPackageDef"

    width:int
    height: int

    def model_post_init(self, __context):
        pins = set([i for i in range(1, self.width * 2 + self.height * 2)])
        pins.difference_update(*[x.to_set() for x in self._power])
        pins.difference_update(self._jtag.to_set())

        self._ordered_pins: List[Pin] = sorted(pins)
        return super().model_post_init(__context)

    @property
    def bringup_pins(self) -> BringupPins:
        return BringupPins(
            core_power=self._power,
            core_clock=2,
            core_reset=1,
            core_heartbeat=self.width * 2 + self.height * 2 - 1,
            core_jtag=self._jtag
        )

    @property
    def _power(self) -> List[PowerPins]:
        """
        The set of power pins for a quad package.
        Power pins are always a matched pair in the middle of a side, with the number
        varying with the size of the package.
        We don't move power pins from these locations to allow for easier bring up test.
        """
        pins = []
        n = (self.width + self.height)//12
        # Left
        p = self.height//2 + self.height//2
        pins.append(PowerPins(p, p +1))
        # Bottom
        start = self.height
        if n > 2:
            p = start + self.width//2 + self.width//2
            pins.append(PowerPins(p, p+1))
        # Right
        start = start + self.width
        if n > 1:
            p = start + self.height//2 + self.height//2
            pins.append(PowerPins(p, p+1))
        # Top
        start = start + self.height
        if n > 3:
            p = start + self.width//2 + self.width//2
            pins.append(PowerPins(p, p+1))
        return pins


    @property
    def _jtag(self) -> JTAGPins:
        """
        Map of JTAG pins for the package
        """
        # Default JTAG pin allocations
        # Use consecutive pins at the start of the package
        start_pin = 2
        return JTAGPins(
            trst=start_pin,
            tck=start_pin + 1,
            tms=start_pin + 2,
            tdi=start_pin + 3,
            tdo=start_pin + 4
        )


class GAPin(NamedTuple):
    h: str
    w: int
    def __lt__(self, other):
        if self.h == other.h:
            return self.w < other.w
        return self.h < other.h


class GALayout(StrEnum):
    FULL = auto()
    PERIMETER = auto()
    CHANNEL = auto()
    ISLAND = auto()


class GAPackageDef(BasePackageDef):
    """Definiton of a grid array package, with pins or pads in a regular array of 'width' by 'height' pins
    on the left and right

    The pins are identified by a 2-tuple of row and column, counting from the bottom left hand corner when looking at the underside of the package.
    Rows are identfied by letter (A-Z), and columns are identified by number.

    The grid may be complete (i.e. width * height pins) or there may be pins/pads missing (Often a square in the middle of the package (AKA P, but this model doesn't
    require this). The missing pins from the grid are identified either by the `missing_pins` field or the `perimeter` field

    Attributes:
        width: The number of pins across on the top and bottom edges
        hieght: The number of pins high on the left and right edges
        layout_type (GALayoutType): Pin layout type
        channel_width: For `GALayoutType.PERIMETER`, `GALayoutType.CHANNEL`, `GALayoutType.ISLAND` the number of initial rows before a gap
        island_width: for `GALayoutType.ISLAND`, the width and height of the inner island
        missing_pins: Used for more exotic types instead of channel_width & island_width. Can be used in conjection with the above.
        additional_pins: Adds pins on top of any of the configuration above

    This includes the following types of package:
    .. csv-table:
    :header: Package, Description
    CPGA, Ceramic Pin Grid Array
    OPGA, Organic Pin Grid Array
    SPGA, Staggared Pin Grid Array
    CABGA: chip array ball grid array
    CBGA and PBGA denote the ceramic or plastic substrate material to which the array is attached.
    CTBGA, thin chip array ball grid array
    CVBGA, very thin chip array ball grid array
    DSBGA, die-size ball grid array
    FBGA, fine ball grid array / fine pitch ball grid array (JEDEC-Standard[9]) or
    FCmBGA, flip chip molded ball grid array
    LBGA, low-profile ball grid array
    LFBGA, low-profile fine-pitch ball grid array
    MBGA, micro ball grid array
    MCM-PBGA, multi-chip module plastic ball grid array
    nFBGA, New Fine Ball Grid Array
    PBGA, plastic ball grid array
    SuperBGA (SBGA), super ball grid array
    TABGA, tape array BGA
    TBGA, thin BGA
    TEPBGA, thermally enhanced plastic ball grid array
    TFBGA or thin and fine ball grid array
    UFBGA and UBGA and ultra fine ball grid array based on pitch ball grid array.
    VFBGA, very fine pitch ball grid array
    WFBGA, very very thin profile fine pitch ball grid array
    wWLB, Embedded wafer level ball grid array
    """

    # Used by pydantic to differentate when deserialising
    package_type: Literal["GAPackageDef"] = "GAPackageDef"

    width:int
    height: int
    layout_type: GALayout= GALayout.FULL
    channel_width: Optional[int]
    island_width: Optional[int]
    missing_pins: Optional[Set[GAPin]]
    additional_pins: Optional[Set[GAPin]]

    def model_post_init(self, __context):
        def int_to_alpha(i: int):
            "Covert int to alpha representation, starting at 1"
            valid_letters = "ABCDEFGHJKLMPRSTUVWXY"
            out = ''
            while i > 0:
                char = i % len(valid_letters)
                i = i // len(valid_letters)
                out = valid_letters[char-1] + out
            return out

        def pins_for_range(h1: int, h2: int, w1: int, w2: int) -> Set[GAPin]:
            pins = [GAPin(int_to_alpha(h),w) for h in range(h1, h2) for w in range(w1, w2)]
            return set(pins)

        def sort_by_quadrant(pins: Set[GAPin]) -> List[Pin]:
            quadrants:List[Set[GAPin]] = [set(), set(), set(), set()]
            midline_h = int_to_alpha(self.height // 2)
            midline_w = self.width // 2
            for pin in pins:
                if pin.h < midline_h and pin.w < midline_w:
                    quadrants[0].add(pin)
                if pin.h >= midline_h and pin.w < midline_w:
                    quadrants[1].add(pin)
                if pin.h < midline_h and pin.w >= midline_w:
                    quadrants[2].add(pin)
                if pin.h >= midline_h and pin.w >= midline_w:
                    quadrants[3].add(pin)
            ret = []
            for q in range(0,3):
                ret.append(sorted(quadrants[q]))
            return ret

        self._ordered_pins: List[Pin] = []
        match self.layout_type:
            case GALayout.FULL:
                pins = pins_for_range(1, self.height, 1, self.width)
                pins -= self.bringup_pins.to_set()
                self._ordered_pins = sort_by_quadrant(pins)

            case GALayout.PERIMETER:
                assert self.channel_width is not None
                pins = pins_for_range(1, self.height, 1, self.width) - \
                       pins_for_range(1 + self.channel_width, self.height-self.channel_width,  1 + self.channel_width, self.width - self.channel_width)
                pins -= self.bringup_pins.to_set()
                self._ordered_pins = sort_by_quadrant(pins)

            case GALayout.ISLAND:
                assert self.channel_width is not None
                assert self.island_width is not None
                outer_pins = pins_for_range(1, self.height, 1, self.width) - \
                             pins_for_range(1 + self.channel_width, self.height-self.channel_width,  1 + self.channel_width, self.width - self.channel_width)
                outer_pins -= self.bringup_pins.to_set()
                inner_pins = pins_for_range(ceil(self.height/ 2 - self.island_width /2), floor(self.height/2 + self.island_width /2),
                                            ceil(self.width / 2 - self.island_width /2), floor(self.width /2 + self.island_width /2))
                # TODO, allocate island as power
                self._ordered_pins = sort_by_quadrant(outer_pins) + sorted(inner_pins)

            case GALayout.CHANNEL:
                assert self.channel_width is not None
                pins = pins_for_range(1, self.channel_width + 1, 1, self.width) | \
                       pins_for_range(self.height - self.channel_width, self.height, 1, self.width)
                pins -= self.bringup_pins.to_set()
                self._ordered_pins = sort_by_quadrant(pins)

        return super().model_post_init(__context)

    def allocate_pins(self, config: 'Config', process: 'Process', lockfile: LockFile|None) -> LockFile:
        portmap = _linear_allocate_components(self._interfaces, lockfile, self._allocate, set(self._ordered_pins))
        bringup_pins = self._allocate_bringup(config)
        portmap.ports['_core']=bringup_pins
        package = self._get_package()
        return LockFile(package=package, process=process, metadata=self._interfaces, port_map=portmap)

    def _allocate(self, available: Set[Pin], width: int) -> List[Pin]:
        avail_n = sorted(available)
        logger.debug(f"GAPackageDef.allocate {width} from {len(avail_n)} remaining: {available}")
        ret = _find_contiguous_sequence(self._ordered_pins, avail_n, width)
        logger.debug(f"GAPackageDef.returned {ret}")
        assert len(ret) == width
        return ret

    @property
    def bringup_pins(self) -> BringupPins:
        return BringupPins(
            core_power=self._power,
            core_clock=2,
            core_reset=1,
            core_heartbeat=self.width * 2 + self.height * 2 - 1,
            core_jtag=self._jtag
        )


    @property
    def _power(self) -> List[PowerPins]:
        return [PowerPins(1,2)]


    @property
    def _jtag(self) -> JTAGPins:
        """
        Map of JTAG pins for the package
        """
        # Default JTAG pin allocations
        # Use consecutive pins at the start of the package
        start_pin = 3
        return JTAGPins(
            trst=start_pin,
            tck=start_pin + 1,
            tms=start_pin + 2,
            tdi=start_pin + 3,
            tdo=start_pin + 4
        )

    @property
    def heartbeat(self) -> Dict[int, Pin]:
        """
        Numbered set of heartbeat pins for the package
        """
        # Default implementation with one heartbeat pin
        # Use the last pin in the package
        return {0: str(self.width * 2 + self.height * 2 - 1)}


class Process(Enum):
    """
    IC manufacturing process
    """
    #: Skywater foundry open-source 130nm process
    SKY130 = "sky130"
    #: GlobalFoundries open-source 130nm process
    GF180 = "gf180"
    #: Pragmatic Semiconductor FlexIC process (old)
    HELVELLYN2 = "helvellyn2"
    #: GlobalFoundries 130nm BCD process
    GF130BCD = "gf130bcd"
    #: IHP open source 130nm SiGe Bi-CMOS process
    IHP_SG13G2 = "ihp_sg13g2"

    def __str__(self):
        return f'{self.value}'


def load_pinlock():
    chipflow_root = _ensure_chipflow_root()
    lockfile = pathlib.Path(chipflow_root, 'pins.lock')
    if lockfile.exists():
        try:
            json = lockfile.read_text()
            return LockFile.model_validate_json(json)
        except pydantic.ValidationError:
            raise ChipFlowError("Lockfile `pins.lock` is misformed. Please remove and rerun chipflow pin lock`")

    raise ChipFlowError("Lockfile `pins.lock` not found. Run `chipflow pin lock`")


def top_components(config):
    component_configs = {}
    result = {}

    # First pass: collect component configs
    for name, conf in config.chipflow.top.items():
        if '.' in name:
            assert isinstance(conf, dict)
            param = name.split('.')[1]
            logger.debug(f"Config {param} = {conf} found for {name}")
            component_configs[param] = conf
        if name.startswith('_'):
            raise ChipFlowError(f"Top components cannot start with '_': {name}")

    # Second pass: instantiate components
    for name, ref in config.chipflow.top.items():
        if '.' not in name:  # Skip component configs, only process actual components
            cls = _get_cls_by_reference(ref, context=f"top component: {name}")
            if name in component_configs:
                result[name] = cls(component_configs[name])
            else:
                result[name] = cls()
            logger.debug(f"top members for {name}:\n{pformat(result[name].metadata.origin.signature.members)}")

    return result
