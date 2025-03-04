import abc
import enum
import itertools
import logging
import pathlib
import pydantic

from collections import OrderedDict, deque
from collections.abc import MutableMapping
from pprint import pformat
from typing import Set, List, Dict, Optional, Union, Literal

from amaranth.lib import wiring, io, meta
from amaranth.lib.wiring import In, Out
from pydantic import BaseModel, ConfigDict

from .. import ChipFlowError, _ensure_chipflow_root, _get_cls_by_reference


__all__ = ['PIN_ANNOTATION_SCHEMA', 'PinSignature',
           'OutputPinSignature', 'InputPinSignature', 'BidirPinSignature',
           'load_pinlock', "PACKAGE_DEFINITIONS", 'top_interfaces']


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


class PinSignature(wiring.Signature):
    """Amaranth Signtaure used to decorate wires that would
    usually be brought out onto a port on the package.

    direction: Input, Output or Bidir
    width: width of port
    all_have_oe: For Bidir ports, should Output Enable be per wire or for the whole port
    init: a  :ref:`const-castable object <lang-constcasting>` for the initial values of the port
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

    def annotations(self, *args):
        annotations = wiring.Signature.annotations(self, *args)
        pin_annotation = _PinAnnotation(direction=self._direction, width=self._width, options=self._options)
        return annotations + (pin_annotation,)

    def __repr__(self):
        opts = ', '.join(f"{k}={v}" for k, v in self._options.items())
        return f"PinSignature({self._direction}, {self._width}, {opts})"


def OutputPinSignature(width, **kwargs):
    return PinSignature(io.Direction.Output, width=width, **kwargs)


def InputPinSignature(width, **kwargs):
    return PinSignature(io.Direction.Input, width=width, **kwargs)


def BidirPinSignature(width, **kwargs):
    return PinSignature(io.Direction.Bidir, width=width, **kwargs)


Pin = Union[tuple, str]
PinSet = Set[Pin]
PinList = List[Pin]
Pins = Union[PinSet, PinList]


class _Side(enum.IntEnum):
    N = 1
    E = 2
    S = 3
    W = 4

    def __str__(self):
        return f'{self.name}'


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


class _BasePackageDef(pydantic.BaseModel, abc.ABC):
    """
    Abstract base class for the definition of a package
    """
    # Used by pydantic to differentate when deserialising,
    # override appropriately when you subclass
    type: Literal["_BasePackageDef"] = "_BasePackageDef"
    name: str

    @property
    @abc.abstractmethod
    def pins(self) -> PinSet:
        ...

    @abc.abstractmethod
    def allocate(self, available: PinSet, width: int) -> PinList:
        ...

    def to_string(pins: Pins):
        return [''.join(map(str, t)) for t in pins]

    def sortpins(self, pins: Pins) -> PinList:
        return list(pins).sort()


class _BareDiePackageDef(_BasePackageDef):
    """Definition of a package with pins on four sides, labelled north, south, east, west
    with an integer identifier within each side.
    """

    # Used by pydantic to differentate when deserialising
    type: Literal["_QuadPackageDef"] = "_QuadPackageDef"

    width: int
    height: int

    def model_post_init(self, __context):
        self._ordered_pins = sorted(
            list(itertools.product((_Side.N, _Side.S), range(self.width))) +
            list(itertools.product((_Side.W, _Side.E), range(self.height))))
        return super().model_post_init(__context)

    @property
    def pins(self) -> PinSet:
        return set(self._ordered_pins)

    def allocate(self, available: PinSet, width: int) -> PinList:
        avail_n = self.sortpins(available)
        logger.debug(f"_BareDiePackageDef.allocate {width} from {len(avail_n)} remaining")
        ret = _find_contiguous_sequence(self._ordered_pins, avail_n, width)
        logger.debug(f"_BareDiePackageDef.returned {ret}")
        assert len(ret) == width
        return ret


class _QuadPackageDef(_BasePackageDef):
    """Definiton of a PGA package with `size` pins

    This is package with `size` pins, numbered, with the assumption that adjacent pins
    are numbered close together.
    """

    # Used by pydantic to differentate when deserialising
    type: Literal["_PGAPackageDef"] = "_PGAPackageDef"

    width:int
    height: int

    def model_post_init(self, __context):
        self._ordered_pins = sorted(
            [str(i) for i in range(1, self.width * 2 + self.height * 2)])
        return super().model_post_init(__context)


    @property
    def pins(self) -> PinSet:
        return set(self._ordered_pins)

    def allocate(self, available: Set[str], width: int) -> List[str]:
        avail_n = sorted(available)
        logger.debug(f"QuadPackageDef.allocate {width} from {len(avail_n)} remaining: {available}")
        ret = _find_contiguous_sequence(self._ordered_pins, avail_n, width)
        logger.debug(f"QuadPackageDef.returned {ret}")
        assert len(ret) == width
        return ret

    def sortpins(self, pins: Union[List[str], Set[str]]) -> List[str]:
        return sorted(list(pins), key=int)


# Add any new package types to both PACKAGE_DEFINITIONS and the PackageDef union
PACKAGE_DEFINITIONS = {
    "pga144": _QuadPackageDef(name="pga144", width=36, height=36),
    "cf20": _BareDiePackageDef(name="cf20", width=7, height=3)
}

PackageDef = Union[_QuadPackageDef, _BasePackageDef]


class Port(pydantic.BaseModel):
    type: str
    pins: List[str]
    direction: Optional[str] = None
    options: Optional[dict] = None

    @property
    def width(self):
        return len(self.pins)


class Package(pydantic.BaseModel):
    package_type: PackageDef = pydantic.Field(discriminator="type")
    power: Dict[str, Port] = {}
    clocks: Dict[str, Port] = {}
    resets: Dict[str, Port] = {}

    def check_pad(self, name: str, defn: dict):
        match defn:
            case {"type": "clock"}:
                return self.clocks[name] if name in self.clocks else None
            case {"type": "reset"}:
                return self.resets[name] if name in self.clocks else None
            case {"type": "power"}:
                return self.power[name] if name in self.power else None
            case {"type": "ground"}:
                return self.power[name] if name in self.power else None
            case _:
                return None

    def add_pad(self, name: str, defn: dict):
        match defn:
            case {"type": "clock", "loc": loc}:
                self.clocks[name] = Port(type="clock", pins=[loc], direction=io.Direction.Input)
            case {"type": "reset", "loc": loc}:
                self.resets[name] = Port(type="reset", pins=[loc], direction=io.Direction.Input)
            case {"type": "power", "loc": loc}:
                self.power[name] = Port(type="power", pins=[loc])
            case {"type": "ground", "loc": loc}:
                self.power[name] = Port(type="ground", pins=[loc])
            case _:
                pass


_Interface = Dict[str, Dict[str, Port]]


class PortMap(pydantic.RootModel[Dict[str, _Interface]], MutableMapping):
    def __getitem__(self, key: str):
        return self.root[key]

    def __setitem__(self, key: str, value: _Interface):
        self.root[key] = value

    def __delitem__(self, key):
        del self.root[key]

    def __iter__(self):
        return iter(self.root)

    def __len__(self):
        return len(self.root)

    def add_port(self, component: str, interface: str, port_name: str, port: Port):
        if component not in self:
            self[component] = {}
        if interface not in self[component]:
            self[component][interface] = {}
        self[component][interface][port_name] = port

    def add_ports(self, component: str, interface: str, ports: Dict[str, Port]):
        if component not in self:
            self[component] = {}
        self[component][interface] = ports

    def get_ports(self, component: str, name: str) -> Dict[str, Port]:
        if component not in self:
            return None
        return self[component][name]


class LockFile(pydantic.BaseModel):
    """
    Representation of a pin lock file.

    Attributes:
        package: Information about package, power, clocks, reset etc
        port_map: Mapping of components to interfaces to port
        metadata: Amaranth metadata, for reference
    """
    package: Package
    port_map: PortMap
    metadata: dict


def load_pinlock():
    chipflow_root = _ensure_chipflow_root()
    lockfile = pathlib.Path(chipflow_root, 'pins.lock')
    if lockfile.exists():
        json = lockfile.read_text()
        return LockFile.model_validate_json(json)
    raise ChipFlowError("Lockfile pins.lock not found. Run `chipflow pin lock`")


def top_interfaces(config):
    interfaces = {}
    top_components = config["chipflow"]["top"].items()
    component_configs = {}
    top = {}

    for name, conf in top_components:
        if '.' in name:
            assert conf is dict
            logger.debug("Config found for {name}")
            component_configs[name.split('.')[0]] = conf

    for name, ref in top_components:
        cls = _get_cls_by_reference(ref, context=f"top component: {name}")
        if name in component_configs:
            top[name] = cls(component_configs[name])
        else:
            top[name] = cls()
        logger.debug(f"top members for {name}:\n{pformat(top[name].metadata.origin.signature.members)}")
        # logger.debug(f"adding\n'{name}':{pformat(top[name].metadata.as_json())} to interfaces")
        interfaces[name] = top[name].metadata.as_json()

    return top, interfaces
