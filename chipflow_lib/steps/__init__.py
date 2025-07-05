"""
Steps provide an extensible way to modify the `chipflow` command behavior for a given design
"""
import logging
import os
from abc import ABC

from amaranth import Module

from ..platforms._utils import IOSignature

logger = logging.getLogger(__name__)

def setup_amaranth_tools():
    _amaranth_settings = {
        "AMARANTH_USE_YOSYS": "system",
        "YOSYS": "yowasp-yosys",
        "SBY": "yowasp-sby",
        "SMTBMC": "yowasp-yosys-smtbmc",
        "NEXTPNR_ICE40": "yowasp-nextpnr-ice40",
        "ICEPACK": "yowasp-icepackr",
        "NEXTPNR_ECP5": "yowasp-nextpnr-ecp5",
        "ECPBRAM": "yowasp-ecpbram",
        "ECPMULTI": "yowasp-ecpmulti",
        "ECPPACK": "yowasp-ecppack",
        "ECPPLL": "yowasp-ecppll",
        "ECPUNPACK": "yowasp-ecpunpack",
        "NEXTPNR-ECP5": "yowasp-nextpnr-ecp5",
        "YOSYS-WITNESS": "yowasp-yosys-witness",
    }

    os.environ |= _amaranth_settings

class StepBase(ABC):
    def __init__(self, config={}):
        ...

    def build_cli_parser(self, parser):
        "Build the cli parser for this step"
        ...

    def run_cli(self, args):
        "Called when this step's is used from `chipflow` command"
        self.build()

    def build(self, *args):
        "builds the design"
        ...

def _wire_up_ports(m: Module, top, platform):
    print("wiring up ports:")
    for n, t in top.items():
        print(">  {n}:{t}")
        setattr(m.submodules, n, t)

    for component, iface in platform._pinlock.port_map.ports.items():
        if component.startswith('_'):
            logger.debug(f"Ignoring special component {component}")
            continue

        for iface_name, member, in iface.items():
            for name, port in member.items():
                iface = getattr(top[component], iface_name)
                logger.debug(f"Wiring up {iface}")
                wire = (iface if isinstance(iface.signature, IOSignature)
                        else getattr(iface, name))
                inv_mask = sum(inv << bit for bit, inv in enumerate(port.invert))
                port = platform._ports[port.port_name]
                if hasattr(wire, 'i'):
                    m.d.comb += wire.i.eq(port.i ^ inv_mask)
                if hasattr(wire, 'o'):
                        m.d.comb += port.o.eq(wire.o^ inv_mask)
                if hasattr(wire, 'oe'):
                        m.d.comb += port.oe.eq(wire.oe ^ inv_mask)

