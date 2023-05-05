# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import tempfile
import subprocess

from amaranth import *
from amaranth.back import rtlil
from amaranth.hdl.ir import Fragment
from amaranth.lib.io import Pin
from amaranth.hdl.xfrm import DomainLowerer

from .providers import silicon as silicon_providers


__all__ = ["SiliconPlatform"]


class SiliconPlatform:
    providers = silicon_providers

    def __init__(self, pads):
        self._pads = pads
        self._pins = {}
        self._files = {}

    def request(self, name):
        if name not in self._pads:
            raise NameError(f"Pad `{name}` is not defined in chipflow.toml")
        if name in self._pins:
            raise NameError(f"Pad `{name}` has already been requested")

        self._pins[name] = Pin(1, dir=self._pads[name]["type"])
        return self._pins[name]

    def add_file(self, filename, content):
        if hasattr(content, "read"):
            content = content.read()
        if isinstance(content, str):
            content = content.encode("utf-8")
        assert isinstance(content, bytes)
        self._files[str(filename)] = content

    def build(self, elaboratable, name="top"):
        # Build RTLIL for the Amaranth design
        fragment = Fragment.get(elaboratable, self)
        fragment._propagate_domains(lambda domain: None, platform=self)
        fragment = DomainLowerer()(fragment)

        ports = []
        for pad_name in self._pins:
            pad, port, pin = self._pads[pad_name], Signal(name=pad_name), self._pins[pad_name]
            ports.append(port)

            if pad["type"] == "io":
                buffer = Instance("buf_io", io_io=port, o_i=pin.i, i_o=pin.o, i_oe=pin.oe)
            elif pad["type"] == "oe":
                buffer = Instance("buf_oe", io_io=port,            i_o=pin.o, i_oe=pin.oe)
            elif pad["type"] == "o":
                buffer = Instance("buf_o",  io_io=port,            i_o=pin.o)
            elif pad["type"] == "i":
                buffer = Instance("buf_i",  io_io=port, o_i=pin.i)
            else:
                assert False, "chipflow.toml does not follow schema"
            fragment.add_subfragment(buffer, name=f"buffer$pad${pad_name}")

        fragment._propagate_ports(ports=ports, all_undef_as_ports=False)
        rtlil_text, _ = rtlil.convert_fragment(fragment, name)

        # Integrate Amaranth design with external Verilog
        yosys_script = [
            b"hierarchy -generate buf_io io:io i:o o:i oe:i",
            b"hierarchy -generate buf_oe io:io     o:i oe:i",
            b"hierarchy -generate buf_o  io:io     o:i",
            b"hierarchy -generate buf_i  io:io i:o",
            b"read_rtlil <<END\n" + rtlil_text.encode("utf-8") + b"\nEND"
        ]
        for filename, content in self._files.items():
            filename_b = filename.encode("utf-8")
            if filename.endswith(".v") or filename.endswith(".vh"):
                yosys_script.append(b"read_verilog -defer <<" + filename_b + b"\n" +
                                    content + b"\n" + filename_b)
            elif filename.endswith(".sv"):
                yosys_script.append(b"read_verilog -defer -sv <<" + filename_b + b"\n" +
                                    content + b"\n" + filename_b)
            else:
                raise ValueError(f"File `{filename}` is not supported by the build platform")
        yosys_script += [
            b"hierarchy"
        ]

        build_dir = os.path.join(os.environ["CHIPFLOW_ROOT"], "build")
        link_script = os.path.join(build_dir, name + "_link.ys")
        with open(link_script, "wb") as script_fp:
            script_fp.write(b"\n".join(yosys_script))
        output_rtlil = os.path.join(build_dir, name + ".il")
        subprocess.check_call(["yowasp-yosys", "-q", link_script, "-o", output_rtlil])
