import json
import logging
import re
import sys

from amaranth import Shape
from pathlib import Path
from pprint import pformat

from chipflow_lib.platforms.iostream import PORT_LAYOUT_SCHEMA
from chipflow_lib.cli import _parse_config, _get_cls_by_reference

logger = logging.getLogger(__name__)

def has_consecutive_numbers(lst):
    if not lst:
        return False
    lst.sort()
    return all(lst[i] + 1 == lst[i + 1] for i in range(len(lst) - 1))

def strip_pin_suffix(name):
    """Strip _i, _o, and _oe suffixes from a pin name.
    
    Args:
        name: Pin name string
        
    Returns:
        Name with suffix removed
    """
    return re.sub(r'(_i|_o|_oe)$', '', name)

def find_consecutive_sequence(lst, n):
    """Find the next sequence of n consecutive numbers in a sorted list.
    
    Args:
        lst: Sorted list of numbers
        n: Length of consecutive sequence to find
        
    Returns:
        A slice indexing the first sequence of n consecutive numbers found within the given list
        or None if no such sequence exists
    """
    if not lst or len(lst) < n:
        return None
        
    for i in range(len(lst) - n + 1):
        if all(lst[i + j] + 1 == lst[i + j + 1] for j in range(n - 1)):
            return slice(i,i + n)
    return None

def signature_width(signature):
    width = 0
    obj = signature.create()
    for a,b,c in signature.flatten(obj):
        shape = Shape.cast(b.shape)
        width += shape.width
    return width

def member_width(member):
    if member.is_signature:
        return signature_width(member.signature)
    else:
        shape = Shape.cast(member.shape)
        return shape.width

MATCH_TRIPLE = re.compile(r'(_i|_o|_oe)$')

def coalesce_triples(sig: dict) -> None:
    if sig['type'] == 'port':
        pass

def count_pins(port):
    width = 0
    for _, v in port.items():
        if type(v) is dict:
            width += count_pins(v)
        else:
            width += v[1]
    return width


def allocate_pins(name, port, pins):
    pin_map = {}
    logger.debug(f"allocate_pins: name={name}, port={port}, pins={pins}")
    for k, v in port.items():
        n = '_'.join([name,k])
        logger.debug(f"{k},{v},{n}")
        if type(v) is dict:
            _map, pins = allocate_pins(n, v, pins)
            pin_map |= _map
            logger.debug(f"{pin_map},{_map}")
        else:
            direction, width = v
            if width == 1:
                pin_map[n] = {'pin':pins[0], 'type':direction}
            else:
                pin_map[n] = {'start':pins[0], 
                                'end':pins[width-1], 
                                'type':direction}
            logger.debug(f"pin_map[{n}]={pin_map[n]}")
            pins = pins[width:]
    return pin_map, pins


def assign_pins(ports, old_lock, unallocated):
    old_ports = old_lock["ports"] if "ports" in old_lock else {}
    old_map = old_lock["map"]["ports"] if "map" in old_lock else {}
    pin_map = {}

    # we try to keep pins together for each port
    for k,v in ports.items():
        logger.debug(f"Port {k}:\n{pformat(v)}")
        width = count_pins(v)
        logger.debug(f"member {k} total width = {width}")

        if k in old_ports:
            logger.debug(f"{k} already has pins defined")
            if width != count_pins(old_ports[k]):
                raise Exception("Port {k} has changed size. Use -c to allocate new pins non-contigously")
            _map = old_map[k]
            old_pins = [v['pin'] for v in old_map[k].values()]
            logger.debug("old pins = {old_pins}")
            unallocated = sorted(list(set(unallocated) - set(old_pins)))
        else:
            pins = find_consecutive_sequence(unallocated, width)
            logger.debug(f"allocated range: {pins}")
            if pins is None:
                raise Exception(f"Error allocating pins for {k},{v} in {ports}")

            
            newpins = unallocated[pins]
            unallocated[pins] = []
            _map,_ = allocate_pins(k, v, newpins)
        
        pin_map[k] = _map
    return pin_map


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
config = _parse_config()
used_pins = set()
pin_map = {}
lockfile = Path('pins.lock')
if lockfile.exists():
    with open(lockfile) as f:
        old_lock = json.load(f)
        old_map = old_lock["map"]
else:
    old_lock = {}
    old_map = {}

for d, default in [("pads", "i"), ("power","pwr")]:
    logger.debug(f"Checking [chipflow.silicon.{d}]:")
    pin_map[d] = {}
    for k, v in config["chipflow"]["silicon"][d].items():
        pin = int(v['loc'])
        used_pins.add(pin)
        if d in old_map and k in old_map[d] and old_map[d][k]['pin'] != pin:
            print(f"chipflow.toml conflicts with pins.lock: "
                  f"{k} had pin {old_map[d][k]}, now {pin}.")
            exit(1)
        pin_map[d][k] = {
            'pin': pin,
            'type': v['type'] if 'type' in v else None}
        

logger.info(f'Pins in use:\n{pformat(sorted(used_pins))}')

unallocated = sorted(set(range(144)) - used_pins)

ports = {}
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
    metadata = top[name].metadata.as_json()
    logger.debug(f"{name}.metadata = {metadata}")
    ports |= metadata['interface']['annotations'][PORT_LAYOUT_SCHEMA]['ports']

logger.debug(f"All ports: {list(ports.keys())}")

pin_map["ports"] = assign_pins(ports, old_lock, unallocated)

with open('pins.lock', 'w') as f:
    newlock = {'map': pin_map,
               'ports': ports}

    json.dump(newlock, f, indent=2, sort_keys=True)
# 
# obj = soc_top.signature.create()
# for a,b,c in soc_top.signature.flatten(obj):
#     pin_name = '_'.join(a)
#     iface = a[0]
#     shape = Shape.cast(b.shape)
#     count = 0
#     for i in pin_map[iface]['pins']:
#         pin_name_i = f'{pin_name}_{count}'
#         count += 1
#         # print(f'pin name {pin_name} {b.flow}')
#         pin_map[iface]['members'][pin_name_i]={'pin':i, 'dir':b.flow}
# 
# # pprint(pin_map)
