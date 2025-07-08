"""
Steps provide an extensible way to modify the `chipflow` command behavior for a given design
"""
import logging
import os
from abc import ABC

from amaranth import Module

from ..platforms.utils import IOSignature

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


def _wire_up_ports(m: Module, top, platform):
    logger.debug("wiring up ports")
    logger.debug("adding top:")
    for n, t in top.items():
        logger.debug(f"    > {n}, {t}")
        setattr(m.submodules, n, t)

    logger.debug("wiring up:")
    for component, iface in platform._pinlock.port_map.items():
        for iface_name, member, in iface.items():
            for name, port in member.items():
                logger.debug(f"    > {component}, {iface_name}, {member}")
                iface = getattr(top[component], iface_name)
                wire = (iface if isinstance(iface.signature, IOSignature)
                        else getattr(iface, name))
                if port.invert:
                    inv_mask = sum(inv << bit for bit, inv in enumerate(port.invert))
                else:
                    inv_mask = 0
                port = platform._ports[port.port_name]
                if hasattr(wire, 'i'):
                    m.d.comb += wire.i.eq(port.i ^ inv_mask)
                if hasattr(wire, 'o'):
                        m.d.comb += port.o.eq(wire.o ^ inv_mask)
                if hasattr(wire, 'oe'):
                        m.d.comb += port.oe.eq(wire.oe)

