import abc
import itertools
import logging
import pathlib
import pydantic


from collections import OrderedDict, deque
from collections.abc import MutableMapping
from dataclasses import dataclass, asdict
from enum import Enum, IntEnum, StrEnum
from math import ceil, floor
from pprint import pformat
from typing import Any, Dict, List, Set, Tuple, Optional, Union, Literal

from amaranth.lib import wiring, io, meta
from amaranth.lib.wiring import In, Out
from pydantic import BaseModel, ConfigDict

from .. import ChipFlowError, _ensure_chipflow_root, _get_cls_by_reference


__all__ = ['PIN_ANNOTATION_SCHEMA', 'IOSignature',
           'OutputIOSignature', 'InputIOSignature', 'BidirIOSignature',
           'load_pinlock', "PACKAGE_DEFINITIONS", 'top_components', 'LockFile',
           'Package', 'PortMap', 'Port',
           'GAPackageDef', 'QuadPackageDef', 'BareDiePackageDef', 'BasePackageDef']


logger = logging.getLogger(__name__)


def _chipflow_schema_uri(name: str, version: int) -> str:
    return f"https://api.chipflow.com/schemas/{version}/{name}"


class _PinAnnotationModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    direction: io.Direction
    width: int
    options: dict = {}

    @classmethod
    def _annotation_schema(cls):
        schema = _PinAnnotationModel.model_json_schema()
        schema['$schema'] = "https://json-schema.org/draft/2020-12/schema"
        schema['$id'] = _chipflow_schema_uri("pin-annotation", 0)
        return schema

    def __init__(self, **kwargs):
        kwargs['url'] = _chipflow_schema_uri("pin-annotation", 0)
        super().__init__(**kwargs)


class _PinAnnotation(meta.Annotation):
    schema = _PinAnnotationModel._annotation_schema()

    def __init__(self, **kwargs):
        self.model = _PinAnnotationModel(**kwargs)

    @property
    def origin(self):  # type: ignore
        return self.model

    def as_json(self):  # type: ignore
        return self.model.model_dump()


PIN_ANNOTATION_SCHEMA = str(_chipflow_schema_uri("pin-annotation", 0))


class IOSignature(wiring.Signature):
    """An :py:obj:`Amaranth Signature <amaranth.lib.wiring.Signature>` used to decorate wires that would usually be brought out onto a port on the package.
    This class is generally not directly used.
    Instead, you would typically utilize the more specific
    :py:obj:`InputIOSignature`, :py:obj:`OutputIOSignature`, or :py:obj:`BidirIOSignature` for defining pin interfaces.

    :param direction: Input, Output or Bidir
    :param width: width of port, default is 1
    :param all_have_oe: controls whether each output wire is associated with an individual Output Enable bit or a single OE bit will be used for entire port, the default value is False, indicating that a single OE bit controls the entire port.
    :param allocate_power: Whether a power line should be allocated with this interface
    :param power_voltage: Voltage range of the allocated power
    :param init: a  :ref:`const-castable object <lang-constcasting>` for the initial values of the port
    """

    def __init__(self, direction: io.Direction, width: int = 1, all_have_oe: bool = False, init = None):
        self._direction = direction
        self._width = width
        self._init = init
        match direction:
            case io.Direction.Bidir:
                sig = {
                    "o": Out(width),
                    "oe": Out(width if all_have_oe else 1),
                    "i": In(width)
                }
            case io.Direction.Input:
                sig = {"i": In(width)}
            case io.Direction.Output:
                sig = {"o": Out(width)}
            case _:
                assert False
        self._options = {
                "all_have_oe": all_have_oe,
                "init": init,
                }

        super().__init__(sig)

    @property
    def direction(self) -> io.Direction:
        "The direction of the IO port"
        return self._direction

    def width(self) -> int:
        "The width of the IO port, in wires"
        return self._width

    def options(self) -> dict:
        """
        Options set on the io port at construction

        Valid options are:
            "all_have_oe": For a bidirectional port, each wire can
            have it's direction dynamically controlled seperately,
            so each wire also has a corresponding Output Enable wire.
            "init": the initial value that this io port will have at power-up and reset.
        """
        return self._options

    def annotations(self, *args):
        annotations = wiring.Signature.annotations(self, *args)
        pin_annotation = _PinAnnotation(direction=self._direction, width=self._width, options=self._options)
        return annotations + (pin_annotation,)

    def __repr__(self):
        opts = ', '.join(f"{k}={v}" for k, v in self._options.items())
        return f"IOSignature({self._direction}, {self._width}, {opts})"


def OutputIOSignature(width, **kwargs):
    """This creates an :py:obj:`Amaranth Signature <amaranth.lib.wiring.Signature>` which is then used to decorate package output signals
    intended for connection to the physical pads of the integrated circuit package.

    :param width: specifies the number of individual output wires within this port, each of which will correspond to a separate physical pad on the integrated circuit package.
    :type width: int
    :param init: a  :ref:`const-castable object <lang-constcasting>` for the initial values of the port
    """
    return IOSignature(io.Direction.Output, width=width, **kwargs)


def InputIOSignature(width, **kwargs):
    """This creates an :py:obj:`Amaranth Signature <amaranth.lib.wiring.Signature>` which is then used to decorate package input signals
    intended for connection to the physical pads of the integrated circuit package.

    :param width: specifies the number of individual input wires within this port, each of which will correspond to a separate physical pad on the integrated circuit package.
    :type width: int
    :param init: a  :ref:`const-castable object <lang-constcasting>` for the initial values of the port
    """
    return IOSignature(io.Direction.Input, width=width, **kwargs)


def BidirIOSignature(width, **kwargs):
    """This creates an :py:obj:`Amaranth Signature <amaranth.lib.wiring.Signature>` which is then used to decorate package bi-directional signals
    intended for connection to the physical pads of the integrated circuit package.

    :param width: specifies the number of individual input/output wires within this port. Each pair of input/output wires will correspond to a separate physical pad on the integrated circuit package.
    :type width: int
    :param all_have_oe: controls whether each output wire is associated with an individual Output Enable bit or a single OE bit will be used for entire port, the default value is False, indicating that a single OE bit controls the entire port.
    :type all_have_oe: bool, optional
    :param init: a  :ref:`const-castable object <lang-constcasting>` for the initial values of the port
    """
    return IOSignature(io.Direction.Bidir, width=width, **kwargs)


Pin = Union[tuple, str, int]
PinSet = Set[Pin]
PinList = List[Pin]
Pins = Union[PinSet, PinList]

class PowerType(StrEnum):
    POWER = "power"
    GROUND = "ground"

class JTAGWire(StrEnum):
    TRST = "trst"
    TCK = "tck"
    TMS = "tms"
    TDI = "tdi"
    TDO = "tdo"

JTAGSignature = wiring.Signature({
    JTAGWire.TRST: Out(InputIOSignature(1)),
    JTAGWire.TCK: Out(InputIOSignature(1)),
    JTAGWire.TMS: Out(InputIOSignature(1)),
    JTAGWire.TDI: Out(InputIOSignature(1)),
    JTAGWire.TDO: Out(OutputIOSignature(1)),
})

@dataclass
class VoltageRange:
    min: Optional[float] = None
    max: Optional[float] = None

@dataclass
class PowerPins:
    "A matched pair of power pins, with optional notation of the voltage range"
    power: Pin
    ground: Pin
    voltage: VoltageRange
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
    core_jtag: JTAGPins

    def to_set(self) -> Set[Pin]:
        return {p for pp in self.core_power for p in asdict(pp).values()} | \
               set([self.core_clock, self.core_reset, self.core_heartbeat]) | \
               self.core_jtag.to_set()


class _Side(IntEnum):
    N = 1
    E = 2
    S = 3
    W = 4

    def __str__(self):
        return f'{self.name}'


class Port(pydantic.BaseModel):
    type: str
    pins: List[str] | None  # None implies must be allocated at end
    port_name: str
    direction: Optional[str] = None
    options: Optional[dict] = None

    @property
    def width(self):
        return len(self.pins) if self.pins else 0


def _group_consecutive_items(ordering: PinList, lst: PinList) -> OrderedDict[int, List[PinList]]:
    if not lst:
        return {}

    grouped = []
    last = lst[0]
    current_group = [last]

    logger.debug(f"_group_consecutive_items starting with {current_group}")

    for item in lst[1:]:
        idx = ordering.index(last)
        next = ordering[idx + 1] if idx < len(ordering) - 1 else None
        logger.debug(f"inspecting {item}, index {idx}, next {next}")
        if item == next:
            current_group.append(item)
            logger.debug("found consecutive, adding to current group")
        else:
            logger.debug("found nonconsecutive, creating new group")
            grouped.append(current_group)
            current_group = [item]
        last = item

    grouped.append(current_group)
    d = {}
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
       and PIN_ANNOTATION_SCHEMA in member['annotations']:
        return member['annotations'][PIN_ANNOTATION_SCHEMA]['width']
    elif member['type'] == 'interface':
        width = 0
        for n, v in member['members'].items():
            width += _count_member_pins('_'.join([name, n]), v)
        return width
    elif member['type'] == 'port':
        return member['width']


def _allocate_pins(name: str, member: Dict[str, Any], pins: List[str], port_name: str = None) -> Tuple[Dict[str, Port], List[str]]:
    "Allocate pins based of Amaranth member metadata"

    if port_name is None:
        port_name = name

    pin_map = {}

    logger.debug(f"allocate_pins: name={name}, pins={pins}")
    logger.debug(f"member={pformat(member)}")

    if member['type'] == 'interface' and 'annotations' in member \
       and PIN_ANNOTATION_SCHEMA in member['annotations']:
        logger.debug("matched IOSignature {sig}")
        sig = member['annotations'][PIN_ANNOTATION_SCHEMA]
        logger.debug(f"matched PinSignature {sig}")
        name = name
        width = sig['width']
        options = sig['options']
        pin_map[name] = {'pins': pins[0:width],
                         'direction': sig['direction'],
                         'type': 'io',
                         'port_name': port_name,
                         'options': options}
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
        logger.warning(f"Port '{name}' has no IOSignature, pin allocation likely to be wrong")
        width = member['width']
        pin_map[name] = {'pins': pins[0:width],
                              'direction': member['dir'],
                              'type': 'io',
                              'port_name': port_name
                              }
        logger.debug(f"added '{name}':{pin_map[name]} to pin_map")
        return pin_map, pins[width:]
    else:
        logging.debug(f"Shouldnt get here. member = {member}")
        assert False


Interface = Dict[str, Port]
Component = Dict[str, Interface]

class PortMap(pydantic.RootModel[Dict[str, Component]], MutableMapping):
    "Represents a mapping of `Port`s to Package pins, grouped by `Component` and  `Interface`"
    def __getitem__(self, key: str):
        "Gets an `Component` from the map by name"
        return self.root[key]

    def __setitem__(self, key: str, value: Component):
        "Adds or modifies a `Component` in the map by name"
        self.root[key] = value

    def __delitem__(self, key):
        "Deletes a `Component` in the map by name"
        del self.root[key]

    def __iter__(self):
        "Iterates `Component`s in the map by name"
        return iter(self.root)

    def __len__(self):
        return len(self.root)

    def _add_port(self, component: str, interface: str, port_name: str, port: Port):
        "Internally used by a `PackageDef`"
        if component not in self:
            self[component] = {}
        if interface not in self[component]:
            self[component][interface] = {}
        self[component][interface][port_name] = port

    def _add_ports(self, component: str, interface: str, ports: Dict[str, Port]):
        "Internally used by a `PackageDef`"
        if component not in self:
            self[component] = {}
        self[component][interface] = ports

    def get_ports(self, component: str, interface: str) -> Dict[str, Port]:
        "List the ports allocated in this PortMap for the given `Component` and `Interface`"
        if component not in self:
            return None
        return self[component][interface]


class LockFile(pydantic.BaseModel):
    """
    Representation of a pin lock file.

    Attributes:
        package: Information about package, power, clocks, reset etc
        port_map: Mapping of components to interfaces to port
        metadata: Amaranth metadata, for reference
    """
    process: 'Process'
    package: 'Package'
    port_map: PortMap
    metadata: dict


PackageDef = Union['GAPackageDef', 'QuadPackageDef', 'BareDiePackageDef', 'BasePackageDef']


class Package(pydantic.BaseModel):
    """
    Serialisable identifier for a defined packaging option
    """
    package_type: PackageDef = pydantic.Field(discriminator="type")


def _linear_allocate_components(interfaces: dict, lockfile: LockFile , allocate, unallocated) -> Tuple[PortMap, PinSet]:
    port_map = PortMap()
    for component, iface in interfaces.items():
        for k, v in iface['interface']['members'].items():
            logger.debug(f"Interface {iface}.{k}:")
            logger.debug(pformat(v))
            width = _count_member_pins(k, v)
            logger.debug(f"  {k}: total {width} pins")
            old_ports = lockfile.port_map.get_ports(component, k) if lockfile else None

            if old_ports:
                logger.debug(f"  {iface}.{k} found in pins.lock, reusing")
                logger.debug(pformat(old_ports))
                old_width = sum([len(p.pins) for p in old_ports.values()])
                if old_width != width:
                    raise ChipFlowError(
                        f"top level interface has changed size. "
                        f"Old size = {old_width}, new size = {width}"
                    )
                port_map._add_ports(component, k, old_ports)
            else:
                pins = allocate(unallocated, width)
                if len(pins) == 0:
                    raise ChipFlowError("No pins were allocated by {package}")
                logger.debug(f"allocated range: {pins}")
                unallocated = unallocated - set(pins)
                _map, _ = _allocate_pins(k, v, pins)
                port_map._add_ports(component, k, _map)
    return port_map


class UnableToAllocate(ChipFlowError):
    pass


class BasePackageDef(pydantic.BaseModel, abc.ABC):
    """
    Abstract base class for the definition of a package
    Serialising this or any derived classes results in the
    description of the package

    Attributes:
        name (str): The name of the package
        lockfile: Optional exisiting LockFile for the mapping

    """

     # Used by pydantic to differentate when deserialising,
    # override appropriately when you subclass
    type: Literal["BasePackageDef"] = "BasePackageDef"
    name: str

    def model_post_init(self, __context):
        self._interfaces = {}
        return super().model_post_init(__context)

    def register_component(self, name: str, component: wiring.Component) -> None:
        """
        Registers a port to be allocated to the pad ring and pins

        Args:
            component: Amaranth `wiring.Component` to allocate

        """
        self._interfaces[name] = component.metadata.as_json()


    @abc.abstractmethod
    def allocate_pins(self, lockfile: Optional[LockFile]) -> LockFile:
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

    def _to_string(pins: Pins):
        return [''.join(map(str, t)) for t in pins]

    def _sortpins(self, pins: Pins) -> PinList:
        return list(pins).sort()


class BareDiePackageDef(BasePackageDef):
    """
    Definition of a package with pins on four sides, labelled north, south, east, west
    with an integer identifier within each side, indicating pads across or down from top-left corner

    Attributes:
        width (int): Number of die pads on top and bottom sides
        height (int): Number of die pads on left and right sides
    """

    # Used by pydantic to differentate when deserialising
    type: Literal["BareDiePackageDef"] = "BareDiePackageDef"

    width: int
    height: int

    def model_post_init(self, __context):
        pins = (
            set(itertools.product((_Side.N, _Side.S), range(self.width)))
            | set(itertools.product((_Side.W, _Side.E), range(self.height)))
            - set(self.bringup_pins.to_set())
        )
        self._ordered_pins = sorted(pins)
        return super().model_post_init(__context)

    def allocate_pins(self, lockfile: LockFile|None) -> 'LockFile':
        return _linear_allocate_components(self._interfaces, lockfile, self._allocate, set(self._ordered_pins))

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


    def _allocate(self, available: PinSet, width: int) -> PinList:
        avail_n = self._sortpins(available)
        logger.debug(f"BareDiePackageDef.allocate {width} from {len(avail_n)} remaining")
        ret = _find_contiguous_sequence(self._ordered_pins, avail_n, width)
        logger.debug(f"BareDiePackageDef.returned {ret}")
        assert len(ret) == width
        return ret



class QuadPackageDef(BasePackageDef):
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
    type: Literal["QuadPackageDef"] = "QuadPackageDef"

    width:int
    height: int
    allocate_jtag: bool = True

    def model_post_init(self, __context):
        pins =(
            set([i for i in range(1, self.width * 2 + self.height * 2)])
            - set(self._power)
            - self._jtag.to_set()
        )
        self._ordered_pins = sorted(pins)
        return super().model_post_init(__context)

    def allocate_pins(self, lockfile: LockFile|None) -> 'LockFile':
        return _linear_allocate_components(self._interfaces, lockfile, self._allocate, set(self._ordered_pins))

    def _allocate(self, available: Set[int], width: int) -> List[int]:
        avail_n = sorted(available)
        logger.debug(f"QuadPackageDef.allocate {width} from {len(avail_n)} remaining: {available}")
        ret = _find_contiguous_sequence(self._ordered_pins, avail_n, width)
        logger.debug(f"QuadPackageDef.returned {ret}")
        assert len(ret) == width
        return ret

    @property
    def bringup_pins(self) -> BringupPins:
        return BringupPins(
            core_power=[self._power],
            core_clock={0: 2},
            core_reset={0: 1},
            core_heartbeat={0: self.width * 2 + self.height * 2 - 1},
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
        pins.append(self.height//2 + self.height//2 +1)
        # Bottom
        start = self.height
        if n > 2:
            pins.append(start + self.width//2 + self.width//2 +1)
        # Right
        start = start + self.width
        if n > 1:
            pins.append(start + self.height//2 + self.height//2 +1)
        # Top
        start = start + self.height
        if n > 3:
            pins.append(start + self.width//2 + self.width//2 +1)
        return pins


    @property
    def _jtag(self) -> JTAGPins:
        """
        Map of JTAG pins for the package
        """
        # Default JTAG pin allocations
        # Use consecutive pins at the start of the package
        start_pin = 2
        if self.allocate_jtag:
            return JTAGPins(
                trst=start_pin,
                tck=start_pin + 1,
                tms=start_pin + 2,
                tdi=start_pin + 3,
                tdo=start_pin + 4
            )
        else:
            return {}

@dataclass
class GAPin:
    h: str
    w: int

class GALayout(StrEnum):
    FULL = "full"
    PERIMETER = "perimeter"
    CHANNEL = "channel"
    ISLAND = "island"

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
    type: Literal["GAPackageDef"] = "GAPackageDef"

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

        def pins_for_range(h1, h2, w1, w2):
            return set([[GAPin(int_to_alpha(h),w) for h in range(h1, h2)] for w in range(w1, w2)])

        def sort_by_quadrant(pins: Set[GAPin]) -> List[GAPin]:
            quadrants = [set(), set(), set(), set()]
            midline_h = int_to_alpha(self.height // 2)
            midline_w = self.width // 2
            for pin in pins:
                if pin.h < midline_h and pin.w < midline_w:
                    quadrants[0] |= pin
                if pin.h >= midline_h and pin.w < midline_w:
                    quadrants[1] != pin
                if pin.h < midline_h and pin.w >= midline_w:
                    quadrants[2] != pin
                if pin.h >= midline_h and pin.w >= midline_w:
                    quadrants[3] != pin
            ret = []
            for q in range(0,3):
                ret.append(sorted(quadrants[q]))
            return ret

        match self.layout_type:
            case GALayout.FULL:
                pins = pins_for_range(1, self.height, 1, self.width)
                pins -= self.bringup_pins.to_set()
                self._ordered_pins = sort_by_quadrant(pins)

            case GALayout.PERIMETER:
                pins = pins_for_range(1, self.height, 1, self.width) - \
                       pins_for_range(1 + self.channel_width, self.height-self.channel_width,  1 + self.channel_width, self.width - self.channel_width)
                pins -= self.bringup_pins.to_set()
                self._ordered_pins = sort_by_quadrant(pins)

            case GALayout.ISLAND:
                outer_pins = pins_for_range(1, self.height, 1, self.width) - \
                             pins_for_range(1 + self.channel_width, self.height-self.channel_width,  1 + self.channel_width, self.width - self.channel_width)
                pins -= self.bringup_pins.to_set()
                inner_pins = pins_for_range(ceil(self.height/ 2 - self.island_width /2), floor(self.height/2 + self.island_width /2),
                                            ceil(self.width / 2 - self.island_width /2), floor(self.width /2 + self.island_width /2))
                # TODO, allocate island as power
                self._ordered_pins = sort_by_quadrant(outer_pins) + sorted(inner_pins)

            case GALayout.CHANNEL:
                pins = pins_for_range(1, self.channel_width + 1, 1, self.width) + \
                       pins_for_range(self.height - self.channel_width, self.height, 1, self.width)
                pins -= self.bringup_pins.to_set()
                self._ordered_pins = sort_by_quadrant(pins)

        return super().model_post_init(__context)


    def allocate_pins(self, lockfile: LockFile|None) -> 'LockFile':
        return _linear_allocate_components(self._interfaces, lockfile, self._allocate, set(self._ordered_pins))

    def _allocate(self, available: Set[str], width: int) -> List[str]:
        avail_n = sorted(available)
        logger.debug(f"GAPackageDef.allocate {width} from {len(avail_n)} remaining: {available}")
        ret = _find_contiguous_sequence(self._ordered_pins, avail_n, width)
        logger.debug(f"GAPackageDef.returned {ret}")
        assert len(ret) == width
        return ret

    @property
    def bringup_pins(self) -> BringupPins:
        return BringupPins(
            core_power=[self._power],
            core_clock={0: str(2)},
            core_reset={0: str(1)},
            core_heartbeat={0: str(self.width * 2 + self.height * 2 - 1)},
            core_jtag=self._jtag
        )


    @property
    def _power(self) -> List[PowerPins]:
        return [PowerPins(1,2)]


    @property
    def _jtag(self) -> Dict[JTAGWire, Pin]:
        """
        Map of JTAG pins for the package
        """
        # Default JTAG pin allocations
        # Use consecutive pins at the start of the package
        start_pin = 3
        return {
            JTAGWire.TRST: str(start_pin),
            JTAGWire.TCK: str(start_pin + 1),
            JTAGWire.TMS: str(start_pin + 2),
            JTAGWire.TDI: str(start_pin + 3),
            JTAGWire.TDO: str(start_pin + 4)
        }

    @property
    def heartbeat(self) -> Dict[int, Pin]:
        """
        Numbered set of heartbeat pins for the package
        """
        # Default implementation with one heartbeat pin
        # Use the last pin in the package
        return {0: str(self.width * 2 + self.height * 2 - 1)}


# Add any new package types to both PACKAGE_DEFINITIONS and the PackageDef union
PACKAGE_DEFINITIONS = {
    "pga144": QuadPackageDef(name="pga144", width=36, height=36),
    "cf20": BareDiePackageDef(name="cf20", width=7, height=3, allocate_jtag=False)
}

class Process(Enum):
    SKY130 = "sky130"
    GF180 = "gf180"
    HELVELLYN2 = "helvellyn2"
    GF130BCD = "gf130bcd"
    IHP_SG13G2 = "ihp_sg13g2"

    def __str__(self):
        return f'{self.value}'


def load_pinlock():
    chipflow_root = _ensure_chipflow_root()
    lockfile = pathlib.Path(chipflow_root, 'pins.lock')
    if lockfile.exists():
        json = lockfile.read_text()
        return LockFile.model_validate_json(json)
    raise ChipFlowError("Lockfile pins.lock not found. Run `chipflow pin lock`")


def top_components(config):
    component_configs = {}
    result = {}

    # First pass: collect component configs
    for name, conf in config["chipflow"]["top"].items():
        if '.' in name:
            assert isinstance(conf, dict)
            logger.debug(f"Config found for {name}")
            component_configs[name.split('.')[0]] = conf

    # Second pass: instantiate components
    for name, ref in config["chipflow"]["top"].items():
        if '.' not in name:  # Skip component configs, only process actual components
            cls = _get_cls_by_reference(ref, context=f"top component: {name}")
            if name in component_configs:
                result[name] = cls(component_configs[name])
            else:
                result[name] = cls()
            logger.debug(f"top members for {name}:\n{pformat(result[name].metadata.origin.signature.members)}")

    return result
