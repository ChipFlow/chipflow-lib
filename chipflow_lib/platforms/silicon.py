# amaranth: UnusedElaboratable=no

# SPDX-License-Identifier: BSD-2-Clause
import copy
import logging
import os
import re
import subprocess

from pprint import pformat
from typing import TYPE_CHECKING, List, Generic

from amaranth import Module, Signal, ClockDomain, ClockSignal, ResetSignal, unsigned
from amaranth.lib import io, data
from amaranth.lib.cdc import FFSynchronizer
from amaranth.back import rtlil  #type: ignore[reportAttributeAccessIssue]
from amaranth.hdl import Fragment
from amaranth.hdl._ir import PortDirection

from .. import ChipFlowError
from ._utils import load_pinlock, PortDesc, Pin, IOModel, IOTripPoint, Process
from ._sky130 import Sky130DriveMode

if TYPE_CHECKING:
    from ..config_models import Config

__all__ = ["SiliconPlatformPort", "SiliconPlatform"]

logger = logging.getLogger(__name__)


class SiliconPlatformPort(io.PortLike, Generic[Pin]):
    def __init__(self,
                 name: str,
                 port_desc: PortDesc):
        self._port_desc = port_desc
        width = port_desc.width

        if 'invert' in port_desc.iomodel:
            if isinstance(port_desc.iomodel['invert'], bool):
                self._invert = [port_desc.iomodel['invert']] * width
            else:
                self._invert = port_desc.iomodel['invert']
        else:
            self._invert = [False] * width

        self._name = name

        # Initialize signal attributes to None
        self._i = None
        self._o = None
        self._oe = None
        self._ie = None

        # Create signals based on direction
        if self.direction in (io.Direction.Input, io.Direction.Bidir):
            self._i = Signal(width, name=f"{self._name}$i")
            self._ie = Signal(width, name=f"{self._name}$ie", init=-1)
        if self.direction in (io.Direction.Output, io.Direction.Bidir):
            init = 0
            if 'init' in port_desc.iomodel and port_desc.iomodel['init']:
                init = port_desc.iomodel['init']
                logger.debug(f"'init' found for self._name. Initialising outputs with {init}")

            self._o = Signal(width, name=f"{self._name}$o", init=init)

            init_oe = -1
            if 'init_oe' in port_desc.iomodel and port_desc.iomodel['init_oe']:
                init_oe = port_desc.iomodel['init_oe']
                logger.debug(f"'init_oe' found for self._name. Initialising oe with {init_oe}")

            # user side either gets single oe or multiple, depending on 'individual_oe'
            # cells side always gets <width> oes. Wired together in the wire method below
            if "individual_oe" not in port_desc.iomodel or not port_desc.iomodel["individual_oe"]:
                self._oe = Signal(1, name=f"{self._name}$oe", init=init_oe)
                self._oes = Signal(width, name=f"{self._name}$oe")
            else:
                self._oes = Signal(width, name=f"{self._name}$oe", init=init_oe)
                self._oe = self._oes
        logger.debug(f"Created SiliconPlatformPort {self._name}, with port description:\n{pformat(self._port_desc)}")

    def instantiate_toplevel(self):
        ports = []
        if self.direction in (io.Direction.Input, io.Direction.Bidir):
            ports.append((f"io${self._name}$i", self._i, PortDirection.Input))
            ports.append((f"io${self._name}$ie", self._ie, PortDirection.Output))
        if self.direction in (io.Direction.Output, io.Direction.Bidir):
            ports.append((f"io${self._name}$o", self._o, PortDirection.Output))
            if self._oe is not None and len(self._oe) == 1 and len(self._oes) > 1:
                ports.append((f"io${self._name}$oe", self._oes, PortDirection.Output))
            else:
                ports.append((f"io${self._name}$oe", self._oe, PortDirection.Output))
        return ports

    def wire_up(self, m, wire):
        assert self.direction == wire.signature.direction  #type: ignore
        # wire user side _oe to _oes if necessary
        if self._oe is not None and len(self._oe) == 1 and len(self._oes) > 1:
            self._oes.eq(self._oe.replicate(len(self._oes)))

        inv_mask = sum(inv << bit for bit, inv in enumerate(self.invert))
        if hasattr(wire, 'i') and wire.i is not None:
            assert self._i is not None
            m.d.comb += wire.i.eq(self._i ^ inv_mask)
        if hasattr(wire, 'o') and wire.o is not None:
            assert self._o is not None
            m.d.comb += self._o.eq(wire.o ^ inv_mask)
        if hasattr(wire, 'oe') and wire.oe is not None:
            assert self._oe is not None
            m.d.comb += self._oe.eq(wire.oe)
        elif self.direction in (io.Direction.Output, io.Direction.Bidir):
            m.d.comb += self._oes.eq(-1)  # set output enabled if the user hasn't connected

        if hasattr(wire, 'ie'):
            assert self._ie is not None
            m.d.comb += self._ie.eq(wire.ie)
        elif self.direction is io.Direction.Bidir:
            assert self._oes is not None
            assert self._ie is not None
            m.d.comb += self._ie.eq(~self._oes)


    @property
    def name(self) -> str:
        return self._name

    @property
    def pins(self) -> List[Pin]:
        return self._port_desc.pins if self._port_desc.pins else []

    @property
    def iomodel(self) -> IOModel:
        return self._port_desc.iomodel


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
    def ie(self):
        if self._ie is None:
            raise AttributeError("SiliconPlatformPort with input direction does not have an "
                                 "input enable signal")
        return self._ie

    @property
    def direction(self):
        return self._port_desc.iomodel['direction']

    @property
    def invert(self):
        return self._invert


    def __len__(self):
        if self.direction is io.Direction.Input:
            return len(self.i)
        if self.direction is io.Direction.Output:
            return len(self.o)
        if self.direction is io.Direction.Bidir:
            assert len(self.i) == len(self.o)
            if 'individual_oe' in self.iomodel and self.iomodel["individual_oe"]:
                assert len(self.o) == len(self.oe)
            else:
                assert len(self.oe) == 1
            return len(self.i)
        assert False  # :nocov:

    def __getitem__(self, key):
        return NotImplemented

    def __invert__(self):
        new_port_desc = copy.deepcopy(self._port_desc)
        new_port_desc.iomodel['invert'] = tuple([ not i for i in self.invert ])
        result = SiliconPlatformPort(self._name, new_port_desc)
        return result

    def __add__(self, other):
        return NotImplemented

    def __repr__(self):
        return (f"SiliconPlatformPort(name={self._name}, iomodel={self.iomodel})")


class Sky130Port(SiliconPlatformPort):
    """
    Specialisation of `SiliconPlatformPort` for the `Skywater sky130_fd_io__gpiov2 IO cell <https://skywater-pdk.readthedocs.io/en/main/contents/libraries/sky130_fd_io/docs/user_guide.html>`_

    Includes wires and configuration for `Drive Modes <IODriveMode>`, `Input buffer trip point <IOTripPoint>`and buffer control
    """

    _DriveMode_map = {
        # Strong pull-up, weak pull-down
        Sky130DriveMode.STRONG_UP_WEAK_DOWN: 0b011,
        # Weak pull-up, Strong pull-down
        Sky130DriveMode.WEAK_UP_STRONG_DOWN: 0b010,
        # Open drain with strong pull-down
        Sky130DriveMode.OPEN_DRAIN_STRONG_DOWN: 0b100,
        # Open drain-with strong pull-up
        Sky130DriveMode.OPEN_DRAIN_STRONG_UP: 0b101,
        # Strong pull-up, weak pull-down
        Sky130DriveMode.STRONG_UP_STRONG_DOWN: 0b110,
        # Weak pull-up, weak pull-down
        Sky130DriveMode.WEAK_UP_WEAK_DOWN: 0b111
    }

    _VTrip_map = {
        # CMOS level switching (30%/70%) referenced to IO power domain
        IOTripPoint.CMOS: (0, 0),
        # TTL level switching (low < 0.8v, high > 2.0v) referenced to IO power domain
        IOTripPoint.TTL: (0, 1),
        # CMOS level switching referenced to core power domain (e.g. low power mode)
        IOTripPoint.VCORE: (1,0),
        # CMOS level switching referenced to external reference voltage (e.g. low power mode)
        # Only available on sky130_fd_io__gpio_ovtv2
        # VREF
    }


    # TODO: slew rate, hold points
    def __init__(self,
                 name: str,
                 port_desc: PortDesc):
        super().__init__(name, port_desc)

        width = port_desc.width

        # keep a list of signals we create
        self._signals = []

        # Port Configuration
        # Input voltage trip level
        if self.direction in (io.Direction.Input, io.Direction.Bidir):
            assert self._i is not None

            if 'trip_point' in port_desc.iomodel:
                trip_point = port_desc.iomodel['trip_point']
                if trip_point not in __class__._VTrip_map:
                    raise ChipFlowError(f"Trip point `{trip_point}` not available for {__class__.__name__}")
                ib_mode_init, vtrip_init = __class__._VTrip_map[trip_point]
            else:
                ib_mode_init = vtrip_init = 0

            self._ib_mode_sel =  Signal(width, name=f"{self._name}$ib_mode_sel", init=ib_mode_init)
            self._signals.append((self._ib_mode_sel, PortDirection.Output))
            self._vtrip_sel = Signal(width, name=f"{self._name}$vtrip_sel", init=vtrip_init)
            self._signals.append((self._vtrip_sel, PortDirection.Output))

        # Drive mode
        if self.direction in (io.Direction.Output, io.Direction.Bidir):
            if self._o is None:
                raise ChipFlowError(f"Cannot set drive modes on a port with no outputs for {name}")
            if 'drive_mode' in port_desc.iomodel:
                dm = Sky130DriveMode(port_desc.iomodel['drive_mode'])
            else:
                dm = Sky130DriveMode.STRONG_UP_STRONG_DOWN
            dm_init = __class__._DriveMode_map[dm]
            dm_init_bits = [ int(b) for b in f"{dm_init:b}"]
            dms_shape = data.ArrayLayout(unsigned(3), width)
            self._dms = Signal(dms_shape, name=f"{self._name}$dms", init=[dm_init] * width)
            all_ones = (2<<(width-1))-1
            self._dm0 = Signal(width, name=f"{self._name}$dm0", init=dm_init_bits[0] * all_ones)
            self._dm1 = Signal(width, name=f"{self._name}$dm1", init=dm_init_bits[1] * all_ones)
            self._dm2 = Signal(width, name=f"{self._name}$dm2", init=dm_init_bits[2] * all_ones)
            self._signals.append((self._dm0, PortDirection.Output))  #type: ignore
            self._signals.append((self._dm1, PortDirection.Output))  #type: ignore
            self._signals.append((self._dm2, PortDirection.Output))  #type: ignore
        # Not enabled yet:
        self._gpio_slow_sel = None  # Select slew rate
        self._gpio_holdover = None  # Hold mode
        # Analog config, not enabled yet
        # see https://skywater-pdk.readthedocs.io/en/main/contents/libraries/sky130_fd_io/docs/user_guide.html#analog-functionality
        self._gpio_analog_en = None # analog enable
        self._gpio_analog_sel = None # analog mux select
        self._gpio_analog_pol = None # analog mux select

    def instantiate_toplevel(self):
        ports = super().instantiate_toplevel()
        for s, d in self._signals:
            logger.debug(f"Instantiating port for signal {repr(s)}")
            logger.debug(f"Instantiating io${s.name} top level port")
            ports.append((f"io${s.name}", s, d))
        return ports

    def wire_up(self, m, wire):
        super().wire_up(m, wire)

        if hasattr(wire, 'drive_mode'):
            m.d.comb += self.drive_mode.eq(wire.drive_mode)

    @property
    def drive_mode(self):
        if self._dms is None:
            raise AttributeError("You can't set the drive mode of an input-only port")
        return self._dms

    #TODO: trip selection

    def __invert__(self):
        new_port_desc = copy.deepcopy(self._port_desc)
        new_port_desc.iomodel['invert'] = tuple([ not i for i in self.invert ])
        result = SiliconPlatformPort(self._name, new_port_desc)
        return result

    def __repr__(self):
        return (f"Sky130Port(name={self._name}, iomodel={self.iomodel})")



def port_for_process(p: Process):
    match p:
        case Process.SKY130:
            return Sky130Port
        case Process.GF180 | Process.HELVELLYN2 | Process.GF130BCD | Process.IHP_SG13G2:
            return SiliconPlatformPort


class IOBuffer(io.Buffer):
    def elaborate(self, platform):
        if not isinstance(self.port, SiliconPlatformPort):
            raise TypeError(f"Cannot elaborate SiliconPlatform buffer with port {self.port!r}")

        m = Module()
        invert = sum(bit << idx for idx, bit in enumerate(self.port.invert))
        if self.direction is not io.Direction.Input:
            if invert != 0:
                o_inv = Signal.like(self.o)
                m.d.comb += o_inv.eq(self.o ^ invert)
            else:
                o_inv = self.o
            m.d.comb += self.port.o.eq(o_inv)
            m.d.comb += self.port.oe.eq(self.oe)
        if self.direction is not io.Direction.Output:
            if invert:
                i_inv = Signal.like(self.i)
                m.d.comb += self.i.eq(i_inv ^ invert)
            else:
                i_inv = self.i
            m.d.comb += i_inv.eq(self.port.i)

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
    def __init__(self, config: 'Config'):
        if not config.chipflow.silicon:
            raise ChipFlowError("I can't build for silicon without a [chipflow.silicon] section to guide me!")
        self._config = config
        self._ports = {}
        self._files = {}
        self._pinlock = None

    @property
    def ports(self):
        return self._ports

    def instantiate_ports(self, m: Module):
        assert self._config.chipflow.silicon
        if hasattr(self, "pinlock"):
            return

        pinlock = load_pinlock()
        for component, iface in pinlock.port_map.ports.items():
            for interface, v in iface.items():
                for name, port_desc in v.items():
                    if port_desc.type == "power":
                        continue
                    self._ports[port_desc.port_name] = port_for_process(self._config.chipflow.silicon.process)(port_desc.port_name, port_desc)

        for clock in pinlock.port_map.get_clocks():
            assert 'clock_domain' in clock.iomodel
            domain = clock.iomodel['clock_domain']
            setattr(m.domains, domain, ClockDomain(name=domain))
            clk_buffer = io.Buffer(io.Direction.Input, self._ports[clock.port_name])
            setattr(m.submodules, "clk_buffer_" + domain, clk_buffer)
            m.d.comb += ClockSignal().eq(clk_buffer.i)  #type: ignore[reportAttributeAccessIssue]

        for reset in pinlock.port_map.get_resets():
            assert 'clock_domain' in reset.iomodel
            domain = reset.iomodel['clock_domain']
            rst_buffer = io.Buffer(io.Direction.Input, self._ports[reset.port_name])
            setattr(m.submodules, reset.port_name, rst_buffer)
            setattr(m.submodules, reset.port_name + "_sync", FFSynchronizer(rst_buffer.i, ResetSignal()))  #type: ignore[reportAttributeAccessIssue]

        self._pinlock = pinlock

    def request(self, name, **kwargs):
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
            result.i = buffer.i  #type: ignore[reportAttributeAccessIssue]
        if buffer.direction is not io.Direction.Input:
            result.o = buffer.o  #type: ignore[reportAttributeAccessIssue]
            result.oe = buffer.oe  #type: ignore[reportAttributeAccessIssue]

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
                raise ChipFlowError(f"Only a single clock domain, called 'sync', may be used: {clock_domain.name}")
            sync_domain = clock_domain

        for subfragment, subfragment_name, src_loc in fragment.subfragments:
            self._check_clock_domains(subfragment, sync_domain)

    def _prepare(self, elaboratable, name="top"):
        fragment = Fragment.get(elaboratable, self)

        # Check that only a single clock domain is used.
        self._check_clock_domains(fragment)

        # Prepare toplevel ports according to pinlock
        ports = []
        for port in self._ports.values():
            ports.extend(port.instantiate_toplevel())

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
