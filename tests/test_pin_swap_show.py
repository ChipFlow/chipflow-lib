# SPDX-License-Identifier: BSD-2-Clause
"""Tests for ``chipflow pin swap`` and ``chipflow pin show``."""

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from amaranth.lib import io

from chipflow import ChipFlowError
from chipflow.config.models import Process
from chipflow.packaging.lockfile import LockFile, Package
from chipflow.packaging.port_desc import PortMap, PortDesc
from chipflow.packaging.standard import BlockPackageDef, BareDiePackageDef
from chipflow.packaging.utils import swap_pins, load_pinlock
from chipflow.packaging.render import render_text, render_svg


def _build_block_lockfile() -> LockFile:
    """A 4×4 BlockPackageDef with bringup (clk=1, rst_n=2) plus two
    user pins on a soc.uart interface (tx=3, rx[0..1]=4,5)."""
    pkg = BlockPackageDef(name="block", width=4, height=4)
    port_map = PortMap(ports={
        "_core": {"bringup_pins": {
            "clk": PortDesc(
                type='clock', pins=[1], port_name='clk',
                iomodel={"width": 1, "direction": io.Direction.Input,
                         "clock_domain": "sync"},
            ),
            "rst_n": PortDesc(
                type='reset', pins=[2], port_name='rst_n',
                iomodel={"width": 1, "direction": io.Direction.Input,
                         "clock_domain": "sync", "invert": True},
            ),
        }},
        "soc": {"uart": {
            "tx": PortDesc(
                type='io', pins=[3], port_name='tx',
                iomodel={"width": 1, "direction": io.Direction.Output},
            ),
            "rx": PortDesc(
                type='io', pins=[4, 5], port_name='rx',
                iomodel={"width": 2, "direction": io.Direction.Input},
            ),
        }},
    })
    return LockFile(
        process=Process.SKY130,
        package=Package(package_type=pkg),
        port_map=port_map,
        metadata={},
    )


@contextmanager
def _chipflow_root_with(lockfile: LockFile):
    """Write the lockfile into a fresh tmpdir set as CHIPFLOW_ROOT,
    flushing the cached root so loaders pick the new one up."""
    from chipflow.utils import ensure_chipflow_root
    old = os.environ.get('CHIPFLOW_ROOT')
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ['CHIPFLOW_ROOT'] = tmpdir
        if hasattr(ensure_chipflow_root, 'root'):
            delattr(ensure_chipflow_root, 'root')
        path = Path(tmpdir) / 'pins.lock'
        path.write_text(lockfile.model_dump_json(indent=2, serialize_as_any=True))
        try:
            yield path
        finally:
            if old is not None:
                os.environ['CHIPFLOW_ROOT'] = old
            else:
                os.environ.pop('CHIPFLOW_ROOT', None)
            if hasattr(ensure_chipflow_root, 'root'):
                delattr(ensure_chipflow_root, 'root')


class SwapPinsTestCase(unittest.TestCase):
    def test_swap_two_user_pins(self):
        with _chipflow_root_with(_build_block_lockfile()):
            swap_pins(3, 4)
            reloaded = load_pinlock()
            ports = reloaded.port_map.ports['soc']['uart']
            # tx had pin 3 → now 4; rx[0] had pin 4 → now 3.
            self.assertEqual(ports['tx'].pins, [4])
            self.assertEqual(ports['rx'].pins, [3, 5])

    def test_swap_within_multi_bit_port(self):
        """Two bits of the same multi-bit port can be swapped."""
        with _chipflow_root_with(_build_block_lockfile()):
            swap_pins(4, 5)
            reloaded = load_pinlock()
            self.assertEqual(
                reloaded.port_map.ports['soc']['uart']['rx'].pins, [5, 4]
            )

    def test_swap_with_self_rejected(self):
        with _chipflow_root_with(_build_block_lockfile()):
            with self.assertRaises(ChipFlowError) as cm:
                swap_pins(3, 3)
            self.assertIn("itself", str(cm.exception))

    def test_swap_unallocated_pin_rejected(self):
        with _chipflow_root_with(_build_block_lockfile()):
            with self.assertRaises(ChipFlowError) as cm:
                swap_pins(3, 99)
            self.assertIn("99", str(cm.exception))
            self.assertIn("not allocated", str(cm.exception))

    def test_swap_bringup_pin_rejected(self):
        """clk lives in _core.bringup_pins → can't swap with a user pin."""
        with _chipflow_root_with(_build_block_lockfile()):
            with self.assertRaises(ChipFlowError) as cm:
                swap_pins(1, 3)
            self.assertIn("bringup", str(cm.exception))

    def test_swap_persists_to_disk(self):
        """After swap, the file on disk reflects the new mapping."""
        with _chipflow_root_with(_build_block_lockfile()) as path:
            swap_pins(3, 5)
            text = path.read_text()
            # Pin 3 should now belong to rx[1], pin 5 to tx — easiest
            # check is to load and inspect.
            after = LockFile.model_validate_json(text)
            self.assertEqual(after.port_map.ports['soc']['uart']['tx'].pins, [5])
            self.assertEqual(
                after.port_map.ports['soc']['uart']['rx'].pins, [4, 3]
            )

    def test_swap_unsupported_pin_type(self):
        """Non-int pin types (e.g. BareDie's (Side, idx)) are rejected
        with a clear message."""
        # Build a minimal BareDie lockfile by hand.
        pkg = BareDiePackageDef(name="bare", width=4, height=4)
        port_map = PortMap(ports={
            "soc": {"uart": {
                "tx": PortDesc(
                    type='io', pins=[("N", 0)], port_name='tx',
                    iomodel={"width": 1, "direction": io.Direction.Output},
                ),
            }},
        })
        lockfile = LockFile(
            process=Process.SKY130,
            package=Package(package_type=pkg),
            port_map=port_map,
            metadata={},
        )
        with _chipflow_root_with(lockfile):
            with self.assertRaises(ChipFlowError) as cm:
                swap_pins(1, 2)
            self.assertIn("integer", str(cm.exception))


class RenderTextTestCase(unittest.TestCase):
    def test_text_lists_all_pins_sorted(self):
        text = render_text(_build_block_lockfile())
        lines = text.strip().splitlines()
        self.assertEqual(lines[0].split()[0], "PIN")
        # Pin column of body rows, in order
        pin_col = [line.split()[0] for line in lines[1:]]
        self.assertEqual(pin_col, ['1', '2', '3', '4', '5'])

    def test_text_includes_port_paths(self):
        text = render_text(_build_block_lockfile())
        self.assertIn("_core.bringup_pins.clk", text)
        self.assertIn("_core.bringup_pins.rst_n", text)
        self.assertIn("soc.uart.tx", text)
        self.assertIn("soc.uart.rx[0]", text)
        self.assertIn("soc.uart.rx[1]", text)


class RenderSvgTestCase(unittest.TestCase):
    def test_svg_basic_shape(self):
        svg = render_svg(_build_block_lockfile())
        self.assertTrue(svg.startswith('<svg'))
        self.assertIn('</svg>', svg)
        # Contains user port labels and bringup labels.
        self.assertIn('_core.bringup_pins.clk', svg)
        self.assertIn('soc.uart.tx', svg)

    def test_svg_unallocated_slots_are_em_dashed(self):
        """A 4×4 block has 16 perimeter slots; we allocated only 5 →
        the rest should render as '—'."""
        svg = render_svg(_build_block_lockfile())
        # At least one em-dash placeholder for the empty slots.
        self.assertIn('—', svg)

    def test_svg_unsupported_package_type(self):
        """BareDie has no SVG renderer yet; should raise cleanly."""
        pkg = BareDiePackageDef(name="bare", width=4, height=4)
        lockfile = LockFile(
            process=Process.SKY130,
            package=Package(package_type=pkg),
            port_map=PortMap(),
            metadata={},
        )
        with self.assertRaises(ChipFlowError) as cm:
            render_svg(lockfile)
        self.assertIn("BareDie", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
