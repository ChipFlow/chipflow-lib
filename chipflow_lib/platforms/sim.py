# SPDX-License-Identifier: BSD-2-Clause

import argparse
import sys
import os
from pathlib import Path

from amaranth import *
from amaranth.back import rtlil


__all__ = ["SimPlatform"]


class SimPlatform:
    from ..providers import sim as providers

    def __init__(self):
        self.build_dir = os.path.join(os.environ['CHIPFLOW_ROOT'], 'build', 'sim')
        self.extra_files = dict()
        self.clk = Signal()
        self.rst = Signal()
        self.buttons = Signal(2)
        self.sim_boxes = dict()

    def add_file(self, filename, content):
        if not isinstance(content, (str, bytes)):
            content = content.read()
        self.extra_files[filename] = content

    def add_model(self, inst_type, iface, edge_det=[]):
        conns = dict(a_keep=True)

        def is_model_out(field_name):
            assert field_name.endswith("_o") or field_name.endswith("_oe") or field_name.endswith("_i"), field_name
            return field_name.endswith("_i")
        for field_name in iface.signature.members:
            if is_model_out(field_name):
                conns[f"o_{field_name}"] = getattr(iface, field_name)
            else:
                conns[f"i_{field_name}"] = getattr(iface, field_name)
        if inst_type not in self.sim_boxes:
            box = 'attribute \\blackbox 1\n'
            box += 'attribute \\cxxrtl_blackbox 1\n'
            box += 'attribute \\keep 1\n'
            box += f'module \\{inst_type}\n'
            for i, ((field_name,), _, field) in enumerate(iface.signature.flatten(iface)):
                field_width = Shape.cast(field.shape()).width
                if field_name in edge_det:
                    box += '  attribute \\cxxrtl_edge "a"\n'
                box += f'  wire width {field_width} {"output" if is_model_out(field_name) else "input"} {i} \\{field_name}\n' # noqa: E501
            box += 'end\n\n'
            self.sim_boxes[inst_type] = box
        return Instance(inst_type, **conns)

    def add_monitor(self, inst_type, iface):
        conns = dict(i_clk=ClockSignal(), a_keep=True)
        for field_name in iface.signature.members:
            conns[f'i_{field_name}'] = getattr(iface, field_name)
        if inst_type not in self.sim_boxes:
            box = 'attribute \\blackbox 1\n'
            box += 'attribute \\cxxrtl_blackbox 1\n'
            box += 'attribute \\keep 1\n'
            box += f'module \\{inst_type}\n'
            box += '  attribute \\cxxrtl_edge "a"\n'
            box += '  wire width 1 input 0 \\clk\n'
            for i, ((field_name,), _, field) in enumerate(iface.signature.flatten(iface)):
                field_width = Shape.cast(field.shape()).width
                box += f'  wire width {field_width} input {i+1} \\{field_name}\n'
            box += 'end\n\n'
            self.sim_boxes[inst_type] = box
        return Instance(inst_type, **conns)

    def build(self, e):
        Path(self.build_dir).mkdir(parents=True, exist_ok=True)

        output = rtlil.convert(e, name="sim_top", ports=[self.clk, self.rst, self.buttons], platform=self)

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
                    print(f"read_rtlil {extra_filename}", file=yosys_file)
                else:
                    print(f"read_verilog -defer {extra_filename}", file=yosys_file)
            print("read_ilang sim_soc.il", file=yosys_file)
            print("hierarchy -top sim_top", file=yosys_file)
            print("write_cxxrtl -g1 -header sim_soc.cc", file=yosys_file)
