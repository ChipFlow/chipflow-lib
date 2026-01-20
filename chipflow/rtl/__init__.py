# SPDX-License-Identifier: BSD-2-Clause
"""RTL integration for ChipFlow.

This module provides infrastructure for integrating external RTL (Verilog,
SystemVerilog, SpinalHDL, etc.) into Amaranth designs via TOML configuration.

Example usage::

    from chipflow.rtl import RTLWrapper, load_wrapper_from_toml

    # Load a timer peripheral from TOML configuration
    timer = load_wrapper_from_toml("wb_timer.toml", generate_dest="build/gen")

    # Add to SoC
    wb_decoder.add(timer.bus, name="timer", addr=TIMER_BASE)
    m.submodules.timer = timer

    # Build a standalone CXXRTL simulator for testing
    sim = timer.build_simulator("build/sim")
    sim.set("i_clk", 1)
    sim.step()
"""

from chipflow.rtl.wrapper import (
    RTLWrapper,
    VerilogWrapper,  # Alias for backwards compatibility
    load_wrapper_from_toml,
    _generate_auto_map,
    _infer_auto_map,
    _parse_verilog_ports,
    _INTERFACE_PATTERNS,
    _INTERFACE_REGISTRY,
)

__all__ = [
    "RTLWrapper",
    "VerilogWrapper",
    "load_wrapper_from_toml",
    "_generate_auto_map",
    "_infer_auto_map",
    "_parse_verilog_ports",
    "_INTERFACE_PATTERNS",
    "_INTERFACE_REGISTRY",
]
