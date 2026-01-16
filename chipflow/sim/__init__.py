# SPDX-License-Identifier: BSD-2-Clause
"""CXXRTL-based simulation infrastructure for ChipFlow.

This module provides Python bindings for CXXRTL simulation, enabling fast
compiled simulation of mixed Amaranth/Verilog/SystemVerilog designs.

Example usage::

    from chipflow.sim import CxxrtlSimulator, build_cxxrtl

    # Build CXXRTL shared library from sources
    lib_path = build_cxxrtl(
        sources=["design.v", "ip.sv"],
        top_module="design",
        output_dir=Path("build/sim")
    )

    # Create simulator and run testbench
    sim = CxxrtlSimulator(lib_path, top_module="design")
    sim.reset()

    # Access signals
    sim.set("clk", 1)
    sim.step()
    value = sim.get("data_out")
"""

from chipflow.sim.cxxrtl import CxxrtlSimulator
from chipflow.sim.build import build_cxxrtl

__all__ = ["CxxrtlSimulator", "build_cxxrtl"]
