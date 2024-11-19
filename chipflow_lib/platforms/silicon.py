# SPDX-License-Identifier: BSD-2-Clause

import os
import subprocess

from amaranth import *
from amaranth.lib import io

from amaranth.back import rtlil
from amaranth.hdl import Fragment
from amaranth.hdl._ir import PortDirection

from .. import ChipFlowError


__all__ = ["SiliconPlatformPort", "SiliconPlatform"]


class SiliconPlatformPort(io.PortLike):
    def __init__(self, name, direction, width, *, invert=False):
        if not isinstance(name, str):
            raise TypeError(f"Name must be a string, not {name!r}")
        if not (isinstance(width, int) and width >= 0):
            raise TypeError(f"Width must be a non-negative integer, not {width!r}")
        if not isinstance(invert, bool):
            raise TypeError(f"'invert' must be a bool, not {invert!r}")

        self._direction = io.Direction(direction)
        self._invert = invert

        self._i = self._o = self._oe = None
        if self._direction in (io.Direction.Input, io.Direction.Bidir):
            self._i = Signal(width, name=f"{name}__i")
        if self._direction in (io.Direction.Output, io.Direction.Bidir):
            self._o = Signal(width, name=f"{name}__o")
            self._oe = Signal(width, name=f"{name}__oe")

    @property
    def i(self):
        if self._i is None:
            raise AttributeError("SiliconPlatformPort with output direction does not have an "
                                 "input signal")
        return self._i

    @property
    def o(self):
        if self._o is None:
            raise AttributeError("SiliconPlatformPort with input direction does not have an "
                                 "output signal")
        return self._o

    @property
    def oe(self):
        if self._oe is None:
            raise AttributeError("SiliconPlatformPort with input direction does not have an "
                                 "output enable signal")
        return self._oe

    @property
    def direction(self):
        return self._direction

    @property
    def invert(self):
        return self._invert

    def __len__(self):
        if self._direction is io.Direction.Input:
            return len(self._i)
        if self._direction is io.Direction.Output:
            assert len(self._o) == len(self._oe)
            return len(self._o)
        if self._direction is io.Direction.Bidir:
            assert len(self._i) == len(self._o) == len(self._oe)
            return len(self._i)
        assert False # :nocov:

    def __getitem__(self, key):
        result = object.__new__(type(self))
        result._i = None if self._i is None else self._i[key]
        result._o = None if self._o is None else self._o[key]
        result._oe = None if self._oe is None else self._oe[key]
        result._invert = self._invert
        result._direction = self._direction
        return result

    def __invert__(self):
        result = object.__new__(type(self))
        result._i = self._i
        result._o = self._o
        result._oe = self._oe
        result._invert = not self._invert
        result._direction = self._direction
        return result

    def __add__(self, other):
        direction = self._direction & other._direction
        result = object.__new__(type(self))
        result._i = None if direction is io.Direction.Output else Cat(self._i, other._i)
        result._o = None if direction is io.Direction.Input else Cat(self._o, other._o)
        result._oe = None if direction is io.Direction.Input else Cat(self._oe, other._oe)
        result._invert = self._invert
        result._direction = direction
        return result


class IOBuffer(io.Buffer):
    def elaborate(self, platform):
        if not isinstance(self.port, SiliconPlatformPort):
            raise TypeError(f"Cannot elaborate SiliconPlatform buffer with port {self.port!r}")

        m = Module()

        if self.direction is not io.Direction.Input:
            if self.port.invert:
                o_inv = Signal.like(self.o)
                m.d.comb += o_inv.eq(~self.o)
            else:
                o_inv = self.o

        if self.direction is not io.Direction.Output:
            if self.port.invert:
                i_inv = Signal.like(self.i)
                m.d.comb += self.i.eq(~i_inv)
            else:
                i_inv = self.i

        if self.direction in (io.Direction.Input, io.Direction.Bidir):
            m.d.comb += i_inv.eq(self.port.i)
        if self.direction in (io.Direction.Output, io.Direction.Bidir):
            m.d.comb += self.port.o.eq(o_inv)
            m.d.comb += self.port.oe.eq(self.oe)

        return m


class FFBuffer(io.FFBuffer):
    def elaborate(self, platform):
        if not isinstance(self.port, SiliconPlatformPort):
            raise TypeError(f"Cannot elaborate SiliconPlatform buffer with port {self.port!r}")

        m = Module()

        m.submodules.io_buffer = io_buffer = IOBuffer(self.direction, self.port)

        if self.direction is not io.Direction.Output:
            i_ff = Signal(reset_less=True)
            m.d[self.i_domain] += i_ff.eq(io_buffer.i)
            m.d.comb += self.i.eq(i_ff)

        if self.direction is not io.Direction.Input:
            o_ff = Signal(reset_less=True)
            oe_ff = Signal(reset_less=True)
            m.d[self.o_domain] += o_ff.eq(self.o)
            m.d[self.o_domain] += oe_ff.eq(self.oe)
            m.d.comb += io_buffer.o.eq(o_ff)
            m.d.comb += io_buffer.oe.eq(oe_ff)

        return m


class SiliconPlatform:
    def __init__(self, pads):
        self._pads = pads
        self._ports = {}
        self._files = {}

    def request(self, name):
        if "$" in name:
            raise NameError(f"Reserved character `$` used in pad name `{name}`")
        if name not in self._pads:
            raise NameError(f"Pad `{name}` is not defined in chipflow.toml")
        if name in self._ports:
            raise NameError(f"Pad `{name}` has already been requested")

        pad_type = self._pads[name]["type"]
        # `clk` is used for clock tree synthesis, but treated as `i` in frontend
        if pad_type in ("i", "clk"):
            direction = io.Direction.Input
        elif pad_type in ("o", "oe"):
            direction = io.Direction.Output
        elif pad_type == "io":
            direction = io.Direction.Bidir
        else:
            assert False

        self._ports[name] = port = SiliconPlatformPort(name, direction, 1)
        return port

    def get_io_buffer(self, buffer):
        if isinstance(buffer, io.Buffer):
            result = IOBuffer(buffer.direction, buffer.port)
        elif isinstance(buffer, io.FFBuffer):
            result = FFBuffer(buffer.direction, buffer.port,
                              i_domain=buffer.i_domain, o_domain=buffer.o_domain)
        else:
            raise TypeError(f"Unsupported buffer type {buffer!r}")

        if buffer.direction is not io.Direction.Output:
            result.i = buffer.i
        if buffer.direction is not io.Direction.Input:
            result.o = buffer.o
            result.oe = buffer.oe

        return result

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
        for port_name, port in self._ports.items():
            if port.direction in (io.Direction.Input, io.Direction.Bidir):
                ports.append((f"io${port_name}$i", port.i, PortDirection.Input))
            if port.direction in (io.Direction.Output, io.Direction.Bidir):
                ports.append((f"io${port_name}$o", port.o, PortDirection.Output))
                ports.append((f"io${port_name}$oe", port.oe, PortDirection.Output))

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
