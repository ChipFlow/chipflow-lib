# SPDX-License-Identifier: BSD-2-Clause

import logging
import os
import sys

from enum import StrEnum
from pathlib import Path
from pprint import pformat
from typing import List, Optional, TypedDict, NotRequired, Unpack, Union

from amaranth import *
from amaranth.lib import io, meta, wiring
from amaranth.back import rtlil  # type: ignore[reportAttributeAccessIssue]
from amaranth.hdl import _ir, _ast
from amaranth.hdl._ir import PortDirection
from amaranth.lib.cdc import FFSynchronizer
from pydantic import BaseModel, ConfigDict

from .. import ChipFlowError
from ._utils import load_pinlock, _chipflow_schema_uri, amaranth_annotate


logger = logging.getLogger(__name__)
__all__ = ["SimPlatform", "SimModelSignature", "BuildObject", "BasicCxxBuild"]


class BuildObject(BaseModel):
    """
    Represents an object built from a compiled language

    Attributes:
        capabilities: arbitary list of capability identifiers
    """
    kind: str = "base"

    @classmethod
    def get_subclasses(cls):
        return tuple(cls.__subclasses__())

class BasicCxxBuild(BuildObject):
    """
    Represents an object built from C++, where the compilation is simply done with a collection of
    cpp and hpp files, simply compiled and linked together with no dependencies

    Attributes:
        cpp_files: C++ files used to define the model
        hpp_files: C++ header files to define the model interfaces
    """
    kind = "basic-c++"
    cpp_files: Optional[List[Path]] = None
    hpp_files: Optional[List[Path]] = None
    hpp_dirs: Optional[List[Path]] = None


SIM_ANNOTATION_SCHEMA = str(_chipflow_schema_uri("sim-model-annotation", 0))


class SimModelCap(StrEnum):
    LOAD_DATA = "load-data"


class SimModel(TypedDict):
    """
    Used to attach simulation models to components

    Attributes:
        cpp_class: C++ class name for the model implmentation
        capabilities: List of capabilities of the model.
        build: A `BuildObject` which contains the described class and implementation
    """
    cpp_class: str
    build: Union[*BuildObject.get_subclasses()]
    capabilities: NotRequired[List[SimModelCap]]

@amaranth_annotate(SimModel, SIM_ANNOTATION_SCHEMA)
class SimModelSignature(wiring.Signature):
    """
    An :py:obj:`Amaranth Signature <amaranth.lib.wiring.Signature>` to be used as the base signature in components that
    have a simulation model.
    """

    def __init__(self, members, **kwargs: Unpack[SimModel]):
        super().__init__(members)

_COMMON_MODELS = BasicCxxBuild(
    cpp_files = [ Path('common','sim','models.cc') ],
    hpp_files = [ Path('common','sim','models.h') ],
    )

class SPIFlashModel(wiring.Component):
    def __init__(self)
        super().__init__(SimModelSignature(cpp_class='spiflash_model', build=_COMMON_MODELS, capabilities=[SimModelCap.LOAD_DATA],
                        members={
                            "clk": Out(OutputIOSignature(1)),
                            "csn": Out(OutputIOSignature(1)),
                            "d": Out(BidirIOSignature(4, all_have_oe=True)),
                        })
#    spiflash_model(const std::string &name, const value<1> &clk, const value<1> &csn, const value<4> &d_o, const value<4> &d_oe, value  <4> &d_i)
UARTModel = SimModelSignature('uart_model', _COMMON_MODELS)
#     uart_model(const std::string &name, const value<1> &tx, value<1> &rx, unsigned baud_div = 25000000/115200)
GPIOModel = SimModelSignature('gpio_model', _COMMON_MODELS)
#    gpio_model(const std::string &name, const value<width> &o, const value<width> &oe, value<width> &i) : name(name), o(o), oe(oe), i(  i)
SPIModel = SimModelSignature('spi_model', _COMMON_MODELS)
#     spi_model(const std::string &name, const value<1> &clk, const value<1> &csn, const value<1> &copi, value<1> &cipo)
I2CModel = SimModelSignature('i2c_model', _COMMON_MODELS)
# i2c_model(const std::string &name, const value<1> &sda_oe, value<1> &sda_i, const value<1> &scl_oe, value<1> &scl_i)
>>>>>>> e5e779df (wip)


def print_fragment(fragment, ports=(), name="top", *, emit_src=True, **kwargs):
    assert isinstance(fragment, (_ir.Fragment, _ir.Design))
    name_map = _ast.SignalDict()
    netlist = _ir.build_netlist(fragment, ports=ports, name=name, **kwargs)
    top = netlist.modules[0]
    print(f"netlist =\n{pformat(netlist)}")
    #print(f"src_loc={netlist.src_loc}")
    print(f"io_ports=\n{pformat(netlist.io_ports)}\n\nsignals={netlist.signals}\n\nsignal_fields={netlist.signal_fields}\n\nname_map={name_map}")


def dump(elaboratable, name="top", platform=None, *, ports=None, emit_src=True, **kwargs):
    if (ports is None and
            hasattr(elaboratable, "signature") and
            isinstance(elaboratable.signature, wiring.Signature)):
        ports = {}
        for path, member, value in elaboratable.signature.flatten(elaboratable):
            if isinstance(value, _ast.ValueCastable):
                value = value.as_value()
            if isinstance(value, _ast.Value):
                if member.flow == wiring.In:
                    dir = _ir.PortDirection.Input
                else:
                    dir = _ir.PortDirection.Output
                ports["__".join(map(str, path))] = (value, dir)
    elif ports is None:
        raise TypeError("The `convert()` function requires a `ports=` argument")
    fragment = _ir.Fragment.get(elaboratable, platform)
    print_fragment(fragment, ports, name, emit_src=emit_src, **kwargs)

class SimPlatform:

    def __init__(self, config):
        self.build_dir = os.path.join(os.environ['CHIPFLOW_ROOT'], 'build', 'sim')
        self.extra_files = dict()
        self.sim_boxes = dict()
        self._ports = {}
        self._config = config
        self._top_sim = {}

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
        dump(e, name="sim_top", ports=ports, platform=self)

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
        with open(main, "w") as main_file:
            for p in self._ports:
                print(p, file=main_file)

    def instantiate_ports(self, m: Module):
        if hasattr(self, "_pinlock"):
            return

        pinlock = load_pinlock()
        for component, iface in pinlock.port_map.ports.items():
            for k, v in iface.items():
                for name, port_desc in v.items():
                    logger.debug(f"Instantiating port {port_desc.port_name}: {port_desc}")
                    invert = port_desc.invert if port_desc.invert else False
                    self._ports[port_desc.port_name] = io.SimulationPort(port_desc.direction, port_desc.width, invert=invert, name=port_desc.port_name)
        for clock in pinlock.port_map.get_clocks():
            assert 'clock_domain' in clock.iomodel
            domain = clock.iomodel['clock_domain']
            logger.debug(f"Instantiating clock buffer for {clock.port_name}, domain {domain}")
            setattr(m.domains, domain, ClockDomain(name=domain))
            clk_buffer = io.Buffer(clock.direction, self._ports[clock.port_name])
            setattr(m.submodules, "clk_buffer_" + clock.port_name, clk_buffer)
            m.d.comb += ClockSignal().eq(clk_buffer.i)  # type: ignore[reportAttributeAccessIssue]

        for reset in pinlock.port_map.get_resets():
            assert 'clock_domain' in reset.iomodel
            domain = reset.iomodel['clock_domain']
            logger.debug(f"Instantiating reset synchronizer for {reset.port_name}, domain {domain}")
            rst_buffer = io.Buffer(reset.direction, self._ports[reset.port_name])
            setattr(m.submodules, reset.port_name, rst_buffer)
            ffsync = FFSynchronizer(rst_buffer.i, ResetSignal())  # type: ignore[reportAttributeAccessIssue]
            setattr(m.submodules, reset.port_name + "_sync", ffsync)

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


