# SPDX-License-Identifier: BSD-2-Clause
"""
Pin allocation algorithms for package definitions.

This module provides algorithms for allocating pins from available
package pads to component interfaces, including intelligent grouping
and contiguous allocation strategies.
"""

import logging
from collections import OrderedDict, deque
from pprint import pformat
from typing import Any, Dict, List, Tuple, Optional

from amaranth.lib import io

from .. import ChipFlowError
from ..platform.io import IO_ANNOTATION_SCHEMA, IOModel
from .pins import PinList
from .port_desc import PortDesc, PortMap
from .lockfile import LockFile

logger = logging.getLogger(__name__)


class UnableToAllocate(ChipFlowError):
    """Raised when pin allocation fails"""
    pass


def _group_consecutive_items(ordering: PinList, lst: PinList) -> OrderedDict[int, List[PinList]]:
    """
    Group items into consecutive sequences based on an ordering.

    Args:
        ordering: The canonical pin ordering
        lst: List of pins to group

    Returns:
        OrderedDict mapping group size to list of groups
    """
    if not lst:
        return OrderedDict()

    grouped = []
    last = lst[0]
    current_group = [last]

    for item in lst[1:]:
        idx = ordering.index(last)
        next = ordering[idx + 1] if idx < len(ordering) - 1 else None
        if item == next:
            current_group.append(item)
        else:
            grouped.append(current_group)
            current_group = [item]
        last = item

    grouped.append(current_group)
    d = OrderedDict()
    for g in grouped:
        d.setdefault(len(g), []).append(g)
    return d


def _find_contiguous_sequence(ordering: PinList, lst: PinList, total: int) -> PinList:
    """
    Find the next sequence of n consecutive pins in a sorted list.

    This tries to allocate pins as contiguously as possible according
    to the canonical pin ordering.

    Args:
        ordering: The canonical pin ordering
        lst: Sorted list of available pins
        total: Number of consecutive pins needed

    Returns:
        List of allocated pins (as contiguous as possible)

    Raises:
        ChipFlowError: If insufficient pins available
    """
    if not lst or len(lst) < total:
        raise ChipFlowError("Invalid request to find_contiguous_sequence")

    grouped = _group_consecutive_items(ordering, lst)

    ret = []
    n = total

    # Start with longest contiguous section, then continue into following sections
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
    """
    Count the pins required for an Amaranth metadata member.

    Args:
        name: Member name (for logging)
        member: Amaranth metadata member dictionary

    Returns:
        Number of pins required
    """
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


def _allocate_pins(name: str, member: Dict[str, Any], pins: List, port_name: Optional[str] = None) -> Tuple[Dict[str, PortDesc], List]:
    """
    Allocate pins based on Amaranth member metadata.

    Args:
        name: Member name
        member: Amaranth metadata member dictionary
        pins: Available pins to allocate from
        port_name: Optional port name override

    Returns:
        Tuple of (pin_map dictionary, remaining pins)
    """
    if port_name is None:
        port_name = name

    pin_map = {}

    logger.debug(f"allocate_pins: name={name}, pins={pins}")
    logger.debug(f"member={pformat(member)}")

    if member['type'] == 'interface' and 'annotations' in member \
       and IO_ANNOTATION_SCHEMA in member['annotations']:
        model: IOModel = member['annotations'][IO_ANNOTATION_SCHEMA]
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
        logging.debug(f"Shouldn't get here. member = {member}")
        assert False


def _linear_allocate_components(interfaces: dict, lockfile: LockFile | None, allocate, unallocated) -> PortMap:
    """
    Allocate pins for components linearly from available pins.

    This is used by LinearAllocPackageDef to allocate pins in order.

    Args:
        interfaces: Component interface metadata
        lockfile: Optional existing lock file to preserve allocations
        allocate: Allocation function (takes unallocated set and width)
        unallocated: Set of unallocated pins

    Returns:
        PortMap with pin allocations

    Raises:
        ChipFlowError: If interface size changed or no pins available
    """
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
