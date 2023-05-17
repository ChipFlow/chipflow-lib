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

from .. import ChipFlowError


__all__ = ["SiliconPlatform"]


class SiliconPlatform:
    from ..providers import silicon as providers

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

    def _check_clock_domains(self, fragment, sync_domain=None):
        for clock_domain in fragment.domains.values():
            if clock_domain.name != "sync" or (sync_domain is not None and
                                               clock_domain is not sync_domain):
                raise ChipFlowError("Only a single clock domain, called 'sync', may be used")
            sync_domain = clock_domain

        for subfragment, subfragment_name in fragment.subfragments:
            self._check_clock_domains(subfragment, sync_domain)

    def _prepare(self, elaboratable, name="top"):
        # Build RTLIL for the Amaranth design
        fragment = Fragment.get(elaboratable, self)
        fragment._propagate_domains(lambda domain: None, platform=self)
        fragment = DomainLowerer()(fragment)

        self._check_clock_domains(fragment)

        ports = []
        for pad_name in self._pins:
            pad, pin = self._pads[pad_name], self._pins[pad_name]

            port_i = Signal(name=f"{pad['loc']}_i")
            port_o = Signal(name=f"{pad['loc']}_o")
            port_oe = Signal(name=f"{pad['loc']}_oe")
            ports += (port_i, port_o, port_oe)

            if pad["type"] == "io":
                fragment.add_statements(
                    pin.i.eq(port_i),
                    port_o.eq(pin.o),
                    port_oe.eq(pin.oe)
                )
            elif pad["type"] == "oe":
                fragment.add_statements(
                    port_o.eq(pin.o),
                    port_oe.eq(pin.oe)
                )
            elif pad["type"] == "o":
                fragment.add_statements(
                    port_o.eq(pin.o),
                    port_oe.eq(1)
                )
            elif pad["type"] == "i":
                fragment.add_statements(
                    pin.i.eq(port_i),
                    port_o.eq(0),
                    port_oe.eq(0)
                )
            else:
                assert False, "chipflow.toml does not follow schema"

            if pad["type"] in ("io", "i"):
                fragment.add_driver(pin.i)
            fragment.add_driver(port_o)
            fragment.add_driver(port_oe)

        fragment._propagate_ports(ports=ports, all_undef_as_ports=False)
        return fragment

    def build(self, elaboratable, name="top"):
        fragment = self._prepare(elaboratable, name)
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
