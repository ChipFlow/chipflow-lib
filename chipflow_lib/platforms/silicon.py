# amaranth: UnusedElaboratable=no

# SPDX-License-Identifier: BSD-2-Clause
import logging
import os
import re
import subprocess

from dataclasses import dataclass

from amaranth import Module, Signal, Cat, ClockDomain, ClockSignal, ResetSignal

from amaranth.lib import wiring, io
from amaranth.lib.cdc import FFSynchronizer
from amaranth.lib.wiring import Component, In, PureInterface

from amaranth.back import rtlil
from amaranth.hdl import Fragment
from amaranth.hdl._ir import PortDirection

from .. import ChipFlowError
from .utils import load_pinlock, Port

__all__ = ["SiliconPlatformPort", "SiliconPlatform"]

logger = logging.getLogger(__name__)


def make_hashable(cls):
    def __hash__(self):
        return hash(id(self))

    def __eq__(self, obj):
        return id(self) == id(obj)

    cls.__hash__ = __hash__
    cls.__eq__ = __eq__
    return cls


HeartbeatSignature = wiring.Signature({"heartbeat_i": In(1)})


@make_hashable
@dataclass
class Heartbeat(Component):
    clock_domain: str = "sync"
    counter_size: int = 23
    name: str = "heartbeat"

    def __init__(self, ports):
        super().__init__(HeartbeatSignature)
        self.ports = ports

    def elaborate(self, platform):
        m = Module()
        # Heartbeat LED (to confirm clock/reset alive)
        heartbeat_ctr = Signal(self.counter_size)
        getattr(m.d, self.clock_domain).__iadd__(heartbeat_ctr.eq(heartbeat_ctr + 1))

        heartbeat_buffer = io.Buffer("o", self.ports.heartbeat)
        m.submodules.heartbeat_buffer = heartbeat_buffer
        m.d.comb += heartbeat_buffer.o.eq(heartbeat_ctr[-1])
        return m


class SiliconPlatformPort(io.PortLike):
    def __init__(self,
                 component: str,
                 name: str,
                 port: Port,
                 *,
                 invert: bool = False):
        self._direction = io.Direction(port.direction)
        self._invert = invert
        self._options = port.options
        self._pins = port.pins

        # Initialize signal attributes to None
        self._i = None
        self._o = None
        self._oe = None

        # Create signals based on direction
        if self._direction in (io.Direction.Input, io.Direction.Bidir):
            self._i = Signal(port.width, name=f"{component}_{name}__i")
        if self._direction in (io.Direction.Output, io.Direction.Bidir):
            self._o = Signal(port.width, name=f"{component}_{name}__o")
        if self._direction is io.Direction.Bidir:
            if "all_have_oe" in self._options and self._options["all_have_oe"]:
                self._oe = Signal(port.width, name=f"{component}_{name}__oe", init=-1)
            else:
                self._oe = Signal(1, name=f"{component}_{name}__oe", init=-1)
        elif self._direction is io.Direction.Output:
            # Always create an _oe for output ports
            self._oe = Signal(1, name=f"{component}_{name}__oe", init=-1)

        logger.debug(f"Created SiliconPlatformPort {name}, width={len(port.pins)},dir{self._direction}")

    def wire(self, m: Module, interface: PureInterface):
        assert self._direction == interface.signature.direction
        if hasattr(interface, 'i'):
            m.d.comb += interface.i.eq(self.i)
        for d in ['o', 'oe']:
            if hasattr(interface, d):
                m.d.comb += getattr(self, d).eq(getattr(interface, d))

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
    def pins(self):
        return self._pins

    @property
    def invert(self):
        return self._invert


    def __len__(self):
        if self._direction is io.Direction.Input:
            return len(self._i)
        if self._direction is io.Direction.Output:
            return len(self._o)
        if self._direction is io.Direction.Bidir:
            assert len(self._i) == len(self._o)
            if self._options["all_have_oe"]:
                assert len(self.o) == len(self._oe)
            else:
                assert len(self._oe) == 1
            return len(self._i)
        assert False  # :nocov:

    def __getitem__(self, key):
        result = object.__new__(type(self))
        result._i = None if self._i is None else self._i[key]
        result._o = None if self._o is None else self._o[key]
        result._oe = None if self._oe is None else self._oe[key]
        result._invert = self._invert
        result._direction = self._direction
        result._options = self._options
        result._pins = self._pins
        return result

    def __invert__(self):
        result = object.__new__(type(self))
        result._i = self._i
        result._o = self._o
        result._oe = self._oe
        result._invert = not self._invert
        result._direction = self._direction
        result._options = self._options
        result._pins = self._pins
        return result

    def __add__(self, other):
        direction = self._direction & other._direction
        result = object.__new__(type(self))
        result._i = None if direction is io.Direction.Output else Cat(self._i, other._i)
        result._o = None if direction is io.Direction.Input else Cat(self._o, other._o)
        result._oe = None if direction is io.Direction.Input else Cat(self._oe, other._oe)
        result._invert = self._invert
        result._direction = direction
        result._options = self._options
        result._pins = self._pins + other._pins
        return result

    def __repr__(self):
        return (f"SiliconPlatformPort(direction={repr(self._direction)}, width={len(self)}, "
                f"i={repr(self._i)}, o={repr(self._o)}, oe={repr(self._oe)}, "
                f"invert={repr(self._invert)})")


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
    def __init__(self, config):
        self._config = config
        self._ports = {}
        self._files = {}

    @property
    def ports(self):
        return self._ports

    def instantiate_ports(self, m: Module):
        if hasattr(self, "pinlock"):
            return

        pinlock = load_pinlock()
        for component, iface in pinlock.port_map.items():
            for k, v in iface.items():
                for name, port in v.items():
                    self._ports[port.port_name] = SiliconPlatformPort(component, name, port)

        for clock, name in self._config["chipflow"]["clocks"].items():
            if name not in pinlock.package.clocks:
                raise ChipFlowError("Unable to find clock {name} in pinlock")

            port_data = pinlock.package.clocks[name]
            port = SiliconPlatformPort(component, name, port_data, invert=True)
            self._ports[name] = port

            if clock == 'default':
                clock = 'sync'
            setattr(m.domains, clock, ClockDomain(name=clock))
            clk_buffer = io.Buffer("i", port)
            setattr(m.submodules, "clk_buffer_" + clock, clk_buffer)
            m.d.comb += ClockSignal().eq(clk_buffer.i)

        for reset, name in self._config["chipflow"]["resets"].items():
            port_data = pinlock.package.resets[name]
            port = SiliconPlatformPort(component, name, port_data)
            self._ports[name] = port
            rst_buffer = io.Buffer("i", port)
            setattr(m.submodules, reset, rst_buffer)
            setattr(m.submodules, reset + "_sync", FFSynchronizer(rst_buffer.i, ResetSignal()))

        self.pinlock = pinlock

    def request(self, name=None, **kwargs):
        if "$" in name:
            raise NameError(f"Reserved character `$` used in pad name `{name}`")
        if name not in self._ports:
            raise NameError(f"Pad `{name}` is not present in the pin lock")
        return self._ports[name]

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

        # Prepare toplevel ports according to pinlock
        ports = []
        for port_name, port in self._ports.items():
            if port.direction in (io.Direction.Input, io.Direction.Bidir):
                ports.append((f"io${port_name}$i", port.i, PortDirection.Input))
            if port.direction in (io.Direction.Output, io.Direction.Bidir):
                ports.append((f"io${port_name}$o", port.o, PortDirection.Output))
            if port.direction is io.Direction.Bidir:
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

        name = re.sub(r"[-_.]+", "_", name).lower()
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

    def default_clock(m, platform, clock, reset):
        # Clock generation
        m.domains.sync = ClockDomain()

        clk = platform.request(clock)
        m.d.comb += ClockSignal().eq(clk.i)
        m.submodules.rst_sync = FFSynchronizer(
            ~platform.request(reset).i,
            ResetSignal())
