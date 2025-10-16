# SPDX-License-Identifier: BSD-2-Clause
"""
Base classes and utilities for ChipFlow platform steps.
"""

import logging
import os

from abc import ABC
from amaranth import Module

from .io import IOSignature
from ..utils import compute_invert_mask

logger = logging.getLogger(__name__)


def setup_amaranth_tools():
    """Configure environment for Amaranth/WASM tools."""
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
    """Base class for ChipFlow build steps."""

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
    """
    Wire up component ports to platform ports based on the pin lock.

    Args:
        m: Amaranth Module to add connections to
        top: Dictionary of top-level components
        platform: Platform instance with _pinlock and _ports
    """
    logger.debug("Wiring up ports")
    logger.debug("-> Adding top components:")
    for n, t in top.items():
        logger.debug(f"    > {n}, {t}")
        setattr(m.submodules, n, t)
    for component, iface in platform._pinlock.port_map.ports.items():
        if component.startswith('_'):
            logger.debug(f"Ignoring special component {component}")
            continue

        for iface_name, member, in iface.items():
            for name, port in member.items():
                logger.debug(f"    > {component}, {iface_name}, {name}: {port}")
                iface = getattr(top[component], iface_name)
                wire = (iface if isinstance(iface.signature, IOSignature)
                        else getattr(iface, name))
                port = platform._ports[port.port_name]
                if hasattr(port, 'wire_up'):
                    port.wire_up(m, wire)
                else:
                    inv_mask = compute_invert_mask(port.invert)
                    if hasattr(wire, 'i'):
                        m.d.comb += wire.i.eq(port.i ^ inv_mask)
                    if hasattr(wire, 'o'):
                            m.d.comb += port.o.eq(wire.o ^ inv_mask)
                    if hasattr(wire, 'oe'):
                            m.d.comb += port.oe.eq(wire.oe)
                    if hasattr(wire, 'ie'):
                            m.d.comb += port.ie.eq(wire.ie)
