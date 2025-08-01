# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
from pathlib import Path

from amaranth import *
from amaranth.lib import io
from amaranth.back import rtlil
from amaranth.hdl._ir import PortDirection
from amaranth.lib.cdc import FFSynchronizer

from .. import ChipFlowError
from .utils import load_pinlock

__all__ = ["SimPlatform"]


class SimPlatform:

    def __init__(self, config):
        self.build_dir = os.path.join(os.environ['CHIPFLOW_ROOT'], 'build', 'sim')
        self.extra_files = dict()
        self.sim_boxes = dict()
        self._ports = {}
        self._config = config

    def add_file(self, filename, content):
        if not isinstance(content, (str, bytes)):
            content = content.read()
        self.extra_files[filename] = content

    def build(self, e):
        Path(self.build_dir).mkdir(parents=True, exist_ok=True)

        ports = []
        for port_name, port in self._ports.items():
            if port.direction in (io.Direction.Input, io.Direction.Bidir):
                ports.append((f"io${port_name}$i", port.i, PortDirection.Input))
            if port.direction in (io.Direction.Output, io.Direction.Bidir):
                ports.append((f"io${port_name}$o", port.o, PortDirection.Output))
            if port.direction is io.Direction.Bidir:
                ports.append((f"io${port_name}$oe", port.oe, PortDirection.Output))

        output = rtlil.convert(e, name="sim_top", ports=ports, platform=self)

        top_rtlil = Path(self.build_dir) / "sim_soc.il"
        with open(top_rtlil, "w") as rtlil_file:
            for box_content in self.sim_boxes.values():
                rtlil_file.write(box_content)
            rtlil_file.write(output)

        top_ys = Path(self.build_dir) / "sim_soc.ys"
        with open(top_ys, "w") as yosys_file:
            for extra_filename, extra_content in self.extra_files.items():
                extra_path = Path(self.build_dir) / extra_filename
                with open(extra_path, "w") as extra_file:
                    extra_file.write(extra_content)
                if extra_filename.endswith(".il"):
                    print(f"read_rtlil {extra_path}", file=yosys_file)
                else:
                    # FIXME: use -defer (workaround for YosysHQ/yosys#4059)
                    print(f"read_verilog {extra_path}", file=yosys_file)
            print("read_rtlil sim_soc.il", file=yosys_file)
            print("hierarchy -top sim_top", file=yosys_file)
            print("write_cxxrtl -header sim_soc.cc", file=yosys_file)

    def instantiate_ports(self, m: Module):
        if hasattr(self, "_pinlock"):
            return

        pinlock = load_pinlock()
        for component, iface in pinlock.port_map.items():
            for k, v in iface.items():
                for name, port in v.items():
                   invert = port.invert if port.invert else False
                   self._ports[port.port_name] = io.SimulationPort(port.direction, port.width, invert=invert, name=f"{component}-{name}")

        for clock, name in self._config["chipflow"]["clocks"].items():
            if name not in pinlock.package.clocks:
                raise ChipFlowError(f"Unable to find clock {name} in pinlock")

            port_data = pinlock.package.clocks[name]
            port = io.SimulationPort(io.Direction.Input, port_data.width, name=f"clock-{name}")
            self._ports[name] = port

            if clock == 'default':
                clock = 'sync'
            setattr(m.domains, clock, ClockDomain(name=clock))
            clk_buffer = io.Buffer("i", port)
            setattr(m.submodules, "clk_buffer_" + clock, clk_buffer)
            m.d.comb += ClockSignal().eq(clk_buffer.i)

        for reset, name in self._config["chipflow"]["resets"].items():
            port_data = pinlock.package.resets[name]
            port = io.SimulationPort(io.Direction.Input, port_data.width, name=f"reset-{name}", invert=True)
            self._ports[name] = port
            rst_buffer = io.Buffer("i", port)
            setattr(m.submodules, reset, rst_buffer)
            setattr(m.submodules, reset + "_sync", FFSynchronizer(rst_buffer.i, ResetSignal()))

        self._pinlock = pinlock




VARIABLES = {
    "OUTPUT_DIR": "./build/sim",
    "ZIG_CXX": f"{sys.executable} -m ziglang c++",
    "CXXFLAGS": "-O3 -g -std=c++17 -Wno-array-bounds -Wno-shift-count-overflow -fbracket-depth=1024",
    "DEFINES": "-DPROJECT_ROOT=\\\"{PROJECT_ROOT}\\\" -DBUILD_DIR=\\\"{BUILD_DIR}\\\"",
    "INCLUDES": "-I {OUTPUT_DIR} -I {COMMON_DIR} -I {COMMON_DIR}/vendor -I {RUNTIME_DIR}",
}
DOIT_CONFIG = {'action_string_formatting': 'both'}

BUILD_SIM = {
        "name": "build_sim",
        "actions": [
            "{ZIG_CXX} {CXXFLAGS} {INCLUDES} {DEFINES} -o {OUTPUT_DIR}/sim_soc{EXE} "
            "{OUTPUT_DIR}/sim_soc.cc {SOURCE_DIR}/main.cc {COMMON_DIR}/models.cc"
            ],
        "targets": [
            "{OUTPUT_DIR}/sim_soc{EXE}"
        ],
        "file_dep": [
            "{OUTPUT_DIR}/sim_soc.cc",
            "{OUTPUT_DIR}/sim_soc.h",
            "{SOURCE_DIR}/main.cc",
            "{COMMON_DIR}/models.cc",
            "{COMMON_DIR}/models.h",
            "{COMMON_DIR}/vendor/nlohmann/json.hpp",
            "{COMMON_DIR}/vendor/cxxrtl/cxxrtl_server.h",
        ],
    }

SIM_CXXRTL = {
        "name": "sim_cxxrtl",
        "actions": ["cd {OUTPUT_DIR} && pdm run yowasp-yosys sim_soc.ys"],
        "targets": ["{OUTPUT_DIR}/sim_soc.cc", "{OUTPUT_DIR}/sim_soc.h"],
        "file_dep": ["{OUTPUT_DIR}/sim_soc.ys", "{OUTPUT_DIR}/sim_soc.il"],
    }

TASKS = [BUILD_SIM, SIM_CXXRTL]


