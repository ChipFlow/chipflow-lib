# SPDX-License-Identifier: BSD-2-Clause

import logging
import os
import sys

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional, Type

from amaranth import Value, ValueCastable, Module, Signal, ClockSignal, ResetSignal, ClockDomain
from amaranth.lib import io, meta, wiring
from amaranth.lib.wiring import In, Out
from amaranth.back import rtlil  # type: ignore[reportAttributeAccessIssue]
from amaranth.hdl._ir import PortDirection
from amaranth.lib.cdc import FFSynchronizer
from jinja2 import Environment, PackageLoader, select_autoescape
from pydantic import BaseModel

from .. import ChipFlowError, _ensure_chipflow_root
from ._signatures import (
        I2CSignature, GPIOSignature, UARTSignature, SPISignature, QSPIFlashSignature,
        SIM_ANNOTATION_SCHEMA, SimInterface
        )
from ._utils import load_pinlock, Interface


logger = logging.getLogger(__name__)
__all__ = ["SimPlatform", "BasicCxxBuilder"]


class SimModelCapability(StrEnum):
    LOAD_DATA = "load-data"


@dataclass
class SimModel:
    """
    Description of a model available from a Builder
    Attributes:
        name: the model name
        signature: the wiring connection of the model. This is also used to match with interfaces.
        capabilities: List of capabilities of the model.
    """
    name: str
    signature: Type[wiring.Signature]
    capabilities: Optional[List[SimModelCapability]] = None

    def __post_init__(self):
        if not hasattr(self.signature, '__chipflow_uid__'):
            raise ChipFlowError(f"Signature {self.signature} must be decorated with `sim_annotate()` to use as a simulation model identifier")


def cxxrtlmangle(name, ispublic=True):
    # RTLIL allows any characters in names other than whitespace. This presents an issue for generating C++ code
    # because C++ identifiers may be only alphanumeric, cannot clash with C++ keywords, and cannot clash with cxxrtl
    # identifiers. This issue can be solved with a name mangling scheme. We choose a name mangling scheme that results
    # in readable identifiers, does not depend on an up-to-date list of C++ keywords, and is easy to apply. Its rules:
    #  1. All generated identifiers start with `_`.
    #  1a. Generated identifiers for public names (beginning with `\`) start with `p_`.
    #  1b. Generated identifiers for internal names (beginning with `$`) start with `i_`.
    #  2. An underscore is escaped with another underscore, i.e. `__`.
    #  3. Any other non-alnum character is escaped with underscores around its lowercase hex code, e.g. `@` as `_40_`.
    out = ''
    if name.startswith('\\'):
        out = 'p_'
        name = name[1:]
    elif name.startswith('$'):
        out = 'i_'
        name = name[1:]
    elif ispublic:
        out = 'p_'
    for c in name:
        if c.isalnum():
            out += c
        elif c == '_':
            out += '__'
        else:
            out += f'_{ord(c):x}_'
    return out


class BasicCxxBuilder(BaseModel):
    """
    Represents an object built from C++, where the compilation is simply done with a collection of
    cpp and hpp files, simply compiled and linked together with no dependencies

    Assumes model name corresponds to the c++ class name and that the class constructors take
    a name followed by the wires of the interface.

    Attributes:
        cpp_files: C++ files used to define the model
        hpp_files: C++ header files to define the model interfaces
    """
    models: List[SimModel]
    cpp_files: List[Path]
    hpp_files: Optional[List[Path]] = None
    hpp_dirs: Optional[List[Path]] = None

    def model_post_init(self, *args, **kwargs):
        self._table = { getattr(m.signature,'__chipflow_uid__'): m for m in self.models }

    def uid_to_c(self, uid: str) -> str:
        return uid.replace('.','__')

    def instantiate_model(self, interface: str, sim_interface: SimInterface, interface_desc: Interface, ports: Dict[str, io.SimulationPort]) -> str:
        uid = sim_interface['uid']
        parameters = sim_interface['parameters']
        if uid not in self._table:
            logger.warn(f"Unable to find simulation model for '{sim_interface}'")

        model = self._table[uid]
        print(getattr(model.signature, '__chipflow_uid__'))
        sig = model.signature(**parameters)
        members = list(sig.flatten(sig.create()))

        sig_names = [ path for path, _, _ in members ]
        port_names = { n: interface_desc[n].port_name for n in interface_desc.keys()}

        identifier_uid = self.uid_to_c(uid)
        names = [f"\\io${port_names[str(n)]}${d}" for n,d in sig_names]
        params = [f"top.{cxxrtlmangle(n)}" for n in names]

        out = f"{model.name} {interface}(\"{interface}\", "
        if len(parameters):
            cpp_params = []
            for p,v in parameters.items():
                cpp_params.append(f"{p} = {v}")
            out += '{' + ', '.join(cpp_params) + '}, '
        out += ', '.join(list(params))
        out += ')\n'
        return out

def find_builder(builders: List[BasicCxxBuilder], sim_interface: SimInterface):
    uid = sim_interface['uid']
    for b in builders:
        if uid in b._table:
            return b
    logger.warn(f"Unable to find builder for '{uid}'")
    return None

_COMMON_BUILDER = BasicCxxBuilder(
    models=[
        SimModel('spi_model', SPISignature),
        SimModel('spiflash_model', QSPIFlashSignature,  [SimModelCapability.LOAD_DATA]),
        SimModel('uart_model', UARTSignature),
        SimModel('i2c_model', I2CSignature),
        SimModel('gpio_model', GPIOSignature),
        ],
    cpp_files=[ Path('{COMMON_DIR}', 'models.cc') ],
    hpp_files=[ Path('models.h') ],
    hpp_dirs=[Path("{COMMON_DIR}")],
    )


class SimPlatform:
    def __init__(self, config):
        self.build_dir = os.path.join(os.environ['CHIPFLOW_ROOT'], 'build', 'sim')
        self.extra_files = dict()
        self.sim_boxes = dict()
        self._ports: Dict[str, io.SimulationPort] = {}
        self._config = config
        self._builders: List[BasicCxxBuilder] = [ _COMMON_BUILDER ]
        self._top_sim = {}
        self._clocks = {}
        self._resets = {}

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

        print("elaborating design")
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
        main = Path(self.build_dir) / "main.cc"

        env = Environment(
            loader=PackageLoader("chipflow_lib", "common/sim"),
            autoescape=select_autoescape()
        )
        template = env.get_template("main.cc.jinja")
        with main.open("w") as main_file:
            print(template.render(
                    includes = [hpp for b in self._builders if b.hpp_files for hpp in b.hpp_files ],
                    initialisers = [exp for exp in self._top_sim.values()],
                    interfaces = [exp for exp in self._top_sim.keys()],
                    clocks = [cxxrtlmangle(f"io${clk}$i") for clk in self._clocks.keys()],
                    resets = [cxxrtlmangle(f"io${rst}$i") for rst in self._resets.keys()],
                    data_load = [{'model_name': 'flash', 'file_name':_ensure_chipflow_root() / 'build'/ 'software'/'software.bin', 'args':[ '0x00100000U' ]}]
                ),
                file=main_file)


    def instantiate_ports(self, m: Module):
        if hasattr(self, "_pinlock"):
            return

        pinlock = load_pinlock()
        for component, iface in pinlock.port_map.ports.items():
            for interface, interface_desc in iface.items():
                for name, port_desc in interface_desc.items():
                    logger.debug(f"Instantiating port {port_desc.port_name}: {port_desc}")
                    invert = port_desc.invert if port_desc.invert else False
                    self._ports[port_desc.port_name] = io.SimulationPort(port_desc.direction, port_desc.width, invert=invert, name=port_desc.port_name)
                if not component.startswith('_') \
                and pinlock.metadata[component]['interface']['members'][interface]['annotations']:
                    sim_interface = pinlock.metadata[component]['interface']['members'][interface]['annotations'][SIM_ANNOTATION_SCHEMA]
                    builder = find_builder(self._builders, sim_interface)
                    if builder:
                        self._top_sim[interface] = builder.instantiate_model(interface, sim_interface, interface_desc, self._ports)

        print(f"ports = {pformat(self._ports)}")
        for clock in pinlock.port_map.get_clocks():
            assert 'clock_domain' in clock.iomodel
            domain = clock.iomodel['clock_domain']
            logger.debug(f"Instantiating clock buffer for {clock.port_name}, domain {domain}")
            setattr(m.domains, domain, ClockDomain(name=domain))
            clk_buffer = io.Buffer(clock.direction, self._ports[clock.port_name])
            setattr(m.submodules, "clk_buffer_" + clock.port_name, clk_buffer)
            m.d.comb += ClockSignal().eq(clk_buffer.i)  # type: ignore[reportAttributeAccessIssue]
            self._clocks[clock.port_name] = self._ports[clock.port_name]

        for reset in pinlock.port_map.get_resets():
            assert 'clock_domain' in reset.iomodel
            domain = reset.iomodel['clock_domain']
            logger.debug(f"Instantiating reset synchronizer for {reset.port_name}, domain {domain}")
            rst_buffer = io.Buffer(reset.direction, self._ports[reset.port_name])
            setattr(m.submodules, reset.port_name, rst_buffer)
            ffsync = FFSynchronizer(rst_buffer.i, ResetSignal())  # type: ignore[reportAttributeAccessIssue]
            setattr(m.submodules, reset.port_name + "_sync", ffsync)
            self._resets[reset.port_name] = self._ports[reset.port_name]

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
            "{OUTPUT_DIR}/sim_soc.cc {OUTPUT_DIR}/main.cc "
            + " ".join([str(p) for p in _COMMON_BUILDER.cpp_files])
            ],
        "targets": [
            "{OUTPUT_DIR}/sim_soc{EXE}"
        ],
        "file_dep": [
            "{OUTPUT_DIR}/sim_soc.cc",
            "{OUTPUT_DIR}/sim_soc.h",
            "{OUTPUT_DIR}/main.cc",
            "{COMMON_DIR}/vendor/nlohmann/json.hpp",
            "{COMMON_DIR}/vendor/cxxrtl/cxxrtl_server.h",
        ] + [str(p) for p in _COMMON_BUILDER.cpp_files],
    }

SIM_CXXRTL = {
        "name": "sim_cxxrtl",
        "actions": ["cd {OUTPUT_DIR} && pdm run yowasp-yosys sim_soc.ys"],
        "targets": ["{OUTPUT_DIR}/sim_soc.cc", "{OUTPUT_DIR}/sim_soc.h"],
        "file_dep": ["{OUTPUT_DIR}/sim_soc.ys", "{OUTPUT_DIR}/sim_soc.il"],
    }

TASKS = [BUILD_SIM, SIM_CXXRTL]


