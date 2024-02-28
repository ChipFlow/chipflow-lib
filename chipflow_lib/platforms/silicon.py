# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import tempfile
import subprocess

from amaranth import *
from amaranth.back import rtlil
from amaranth.hdl import Fragment
from amaranth.lib.io import Pin
from amaranth.hdl._ir import PortDirection

from .. import ChipFlowError


__all__ = ["SiliconPlatform"]


class SiliconPlatform:
    from ..providers import silicon as providers

    def __init__(self, pads):
        self._pads = pads
        self._pins = {}
        self._files = {}

    def request(self, name):
        if "$" in name:
            raise NameError(f"Reserved character `$` used in pad name `{name}`")
        if name not in self._pads:
            raise NameError(f"Pad `{name}` is not defined in chipflow.toml")
        if name in self._pins:
            raise NameError(f"Pad `{name}` has already been requested")

        pin_type = self._pads[name]["type"]
        if pin_type == "clk":
            pin_type = "i" # `clk` is used for clock tree synthesis, but treated as `i` in frontend
        self._pins[name] = Pin(1, dir=pin_type)
        return self._pins[name]

    def add_file(self, filename, content):
        if hasattr(content, "read"):
            content = content.read()
        if isinstance(content, str):
            content = content.encode("utf-8")
        assert isinstance(content, bytes)
        self._files[str(filename)] = content

    def _check_clock_domains(self, fragment, sync_domain=None):
        for clock_domain in fragment.domains.values():
            if clock_domain.name != "sync" or (sync_domain is not None and
                                               clock_domain is not sync_domain):
                raise ChipFlowError("Only a single clock domain, called 'sync', may be used")
            sync_domain = clock_domain

        for subfragment, subfragment_name, src_loc in fragment.subfragments:
            self._check_clock_domains(subfragment, sync_domain)

    def _prepare(self, elaboratable, name="top"):
        fragment = Fragment.get(elaboratable, self)

        # Check that only a single clock domain is used.
        self._check_clock_domains(fragment)

        # Prepare toplevel ports according to chipflow.toml.
        ports = []
        for pad_name in self._pins:
            pad, pin = self._pads[pad_name], self._pins[pad_name]
            if pad["type"] in ("io", "i", "clk"):
                ports.append((f"io${pad_name}$i", pin.i, PortDirection.Input))
            if pad["type"] in ("oe", "io", "o"):
                ports.append((f"io${pad_name}$o", pin.o, PortDirection.Output))
            if pad["type"] in ("oe", "io"):
                ports.append((f"io${pad_name}$oe", pin.oe, PortDirection.Output))

        # Prepare design for RTLIL conversion.
        return fragment.prepare(ports)

    def build(self, elaboratable, name="top"):
        fragment = self._prepare(elaboratable, name)
        rtlil_text, _ = rtlil.convert_fragment(fragment, name)

        # Integrate Amaranth design with external Verilog
        yosys_script = [
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
        os.makedirs(build_dir, exist_ok=True)

        link_script = os.path.join(build_dir, name + "_link.ys")
        with open(link_script, "wb") as script_fp:
            script_fp.write(b"\n".join(yosys_script))
        output_rtlil = os.path.join(build_dir, name + ".il")
        subprocess.check_call([
            # yowasp supports forward slashes *only*
            "yowasp-yosys", "-q", link_script.replace("\\", "/"),
            "-o", output_rtlil.replace("\\", "/")
        ])
        return output_rtlil
