# SPDX-License-Identifier: BSD-2-Clause
"""Tests for chipflow.rtl.blackbox (load_blackbox_wrapper + bundle layout)."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from chipflow import ChipFlowError
from chipflow.rtl.blackbox import BlackboxWrapper, load_blackbox_wrapper


def _minimal_blackbox(
    name: str = "MACRO",
    pins: list[dict] | None = None,
    files: dict[str, str] | None = None,
) -> dict:
    if pins is None:
        pins = [
            {"name": "CLK", "direction": "in", "width": 1,
             "msb": 0, "lsb": 0, "role": "clock"},
            {"name": "RST_N", "direction": "in", "width": 1,
             "msb": 0, "lsb": 0, "role": "signal"},
            {"name": "DIN", "direction": "in", "width": 8,
             "msb": 7, "lsb": 0, "role": "signal"},
            {"name": "DOUT", "direction": "out", "width": 8,
             "msb": 7, "lsb": 0, "role": "signal"},
            {"name": "VDD", "direction": "inout", "width": 1,
             "msb": 0, "lsb": 0, "role": "power"},
            {"name": "VSS", "direction": "inout", "width": 1,
             "msb": 0, "lsb": 0, "role": "ground"},
        ]
    bb: dict = {
        "version": "1",
        "name": name,
        "boundary": {"width": 100.0, "height": 50.0},
        "pins": pins,
    }
    if files is not None:
        bb["files"] = files
    return bb


class _ProjectFixture:
    """Creates a self-contained chipflow.toml + blackbox tree on disk."""

    def __init__(self, tmpdir: Path, macros_section: str, blackboxes: dict[str, dict],
                 stubs: dict[str, str] | None = None,
                 extras: dict[str, dict[str, bytes]] | None = None):
        self.root = tmpdir
        (tmpdir / "chipflow.toml").write_text(
            '[chipflow]\n'
            'project_name = "test"\n'
            '\n'
            '[chipflow.silicon]\n'
            'process = "sky130"\n'
            'package = "caravel"\n'
            f'{macros_section}'
        )
        self.blackbox_paths: dict[str, Path] = {}
        for rel_path, bb in blackboxes.items():
            full = tmpdir / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(json.dumps(bb))
            self.blackbox_paths[rel_path] = full
        for stub_rel, content in (stubs or {}).items():
            full = tmpdir / stub_rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
        for rel_dir, files in (extras or {}).items():
            base = tmpdir / rel_dir
            base.mkdir(parents=True, exist_ok=True)
            for fname, content in files.items():
                (base / fname).write_bytes(content)


class LoadBlackboxWrapperTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        # Reset the cached CHIPFLOW_ROOT between tests.
        from chipflow.utils import ensure_chipflow_root
        if hasattr(ensure_chipflow_root, "root"):
            delattr(ensure_chipflow_root, "root")
        self._prev_root = os.environ.get("CHIPFLOW_ROOT")
        os.environ["CHIPFLOW_ROOT"] = str(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self._prev_root is None:
            os.environ.pop("CHIPFLOW_ROOT", None)
        else:
            os.environ["CHIPFLOW_ROOT"] = self._prev_root
        from chipflow.utils import ensure_chipflow_root
        if hasattr(ensure_chipflow_root, "root"):
            delattr(ensure_chipflow_root, "root")

    def _fixture(self, **kwargs):
        return _ProjectFixture(self.tmpdir, **kwargs)

    def test_signature_skips_power_ground_clock_reset(self):
        stub = (
            "module MACRO(input CLK, input RST_N, "
            "input [7:0] DIN, output [7:0] DOUT); endmodule\n"
        )
        self._fixture(
            macros_section=(
                '[chipflow.silicon.macros.m1]\n'
                'blackbox = "vendor/m1.blackbox.json"\n'
            ),
            blackboxes={
                "vendor/m1.blackbox.json": _minimal_blackbox(
                    files={"verilog_stub": "m1.v"},
                ),
            },
            stubs={"vendor/m1.v": stub},
        )

        w = load_blackbox_wrapper(
            "m1", clocks={"sys": "CLK"}, resets={"sys": "RST_N"},
        )
        members = set(w.signature.members.keys())
        # Power/ground dropped, clock/reset dropped, signals kept
        self.assertEqual(members, {"DIN", "DOUT"})
        self.assertIsInstance(w, BlackboxWrapper)

    def test_unknown_macro_errors(self):
        self._fixture(
            macros_section='',
            blackboxes={},
        )
        with self.assertRaisesRegex(ChipFlowError, "not declared"):
            load_blackbox_wrapper("ghost")

    def test_missing_clock_pin_errors(self):
        self._fixture(
            macros_section=(
                '[chipflow.silicon.macros.m1]\n'
                'blackbox = "m1.blackbox.json"\n'
            ),
            blackboxes={"m1.blackbox.json": _minimal_blackbox()},
        )
        with self.assertRaisesRegex(ChipFlowError, "NOTAPIN"):
            load_blackbox_wrapper("m1", clocks={"sys": "NOTAPIN"})

    def test_unsupported_version_errors(self):
        bb = _minimal_blackbox()
        bb["version"] = "99"
        self._fixture(
            macros_section=(
                '[chipflow.silicon.macros.m1]\n'
                'blackbox = "m1.blackbox.json"\n'
            ),
            blackboxes={"m1.blackbox.json": bb},
        )
        with self.assertRaisesRegex(ChipFlowError, "version"):
            load_blackbox_wrapper("m1")

    def test_inout_signal_pin_rejected(self):
        pins = [
            {"name": "DATA", "direction": "inout", "width": 1,
             "msb": 0, "lsb": 0, "role": "signal"},
        ]
        self._fixture(
            macros_section=(
                '[chipflow.silicon.macros.m1]\n'
                'blackbox = "m1.blackbox.json"\n'
            ),
            blackboxes={"m1.blackbox.json": _minimal_blackbox(pins=pins)},
        )
        with self.assertRaisesRegex(ChipFlowError, "inout"):
            load_blackbox_wrapper("m1")

    def test_elaborate_calls_add_macro(self):
        self._fixture(
            macros_section=(
                '[chipflow.silicon.macros.m1]\n'
                'blackbox = "m1.blackbox.json"\n'
            ),
            blackboxes={"m1.blackbox.json": _minimal_blackbox()},
        )
        w = load_blackbox_wrapper(
            "m1", clocks={"sys": "CLK"}, resets={"sys": "RST_N"},
        )
        platform = mock.MagicMock()
        w.elaborate(platform)
        platform.add_macro.assert_called_once_with("m1")


class BuildBundleWithMacrosTestCase(unittest.TestCase):
    """`_build_bundle_zip` packs registered macros into the same zip and
    surfaces them in the manifest under `macros/<logical_name>/` with
    `_file`-suffixed paths (which the chipflow-backend's recursive
    extractor walks for)."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.rtlil = self.tmpdir / "top.il"
        self.rtlil.write_text("module top(); endmodule\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _entry(self, logical: str, cell: str) -> dict:
        subdir = self.tmpdir / logical
        subdir.mkdir(parents=True, exist_ok=True)
        lef = subdir / f"{cell}.lef"
        lef.write_text(f"# LEF for {cell}\n")
        gds = subdir / f"{cell}.gds"
        gds.write_bytes(b"\x00\x01BINARY\xff")
        bb_path = subdir / f"{cell}.blackbox.json"
        bb_path.write_text('{"version": "1"}')
        return {
            "logical_name": logical,
            "name": cell,
            "blackbox_json": bb_path,
            "blackbox": {"version": "1"},
            "files": {"lef": lef, "frame_gds": gds},
        }

    def test_no_macros_omits_macros_key(self):
        from chipflow.platform.silicon_step import _build_bundle_zip
        blob = _build_bundle_zip(
            self.rtlil, "{}", "p", "sky130", "cf20", macros=None)
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            manifest = json.loads(zf.read("manifest.json"))
            self.assertNotIn("macros", manifest)

    def test_macros_packed_under_macros_subfolder(self):
        from chipflow.platform.silicon_step import _build_bundle_zip
        macros = {
            "sram": self._entry("sram", "SRAM_64X64"),
            "pll":  self._entry("pll",  "PLL_CORE"),
        }
        blob = _build_bundle_zip(
            self.rtlil, '{"pins": []}', "myproj", "ihp_sg13g2", "pga144",
            macros=macros)

        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            names = set(zf.namelist())
            self.assertIn("manifest.json", names)
            self.assertIn("top.il", names)
            self.assertIn("pins.lock", names)
            self.assertIn("macros/sram/SRAM_64X64.lef", names)
            self.assertIn("macros/sram/SRAM_64X64.gds", names)
            self.assertIn("macros/sram/SRAM_64X64.blackbox.json", names)
            self.assertIn("macros/pll/PLL_CORE.lef", names)

            manifest = json.loads(zf.read("manifest.json"))
            self.assertEqual(manifest["version"], "1")
            self.assertEqual(manifest["project"], "myproj")
            self.assertEqual(manifest["process"], "ihp_sg13g2")
            self.assertEqual(manifest["package"], "pga144")
            self.assertEqual(manifest["design_file"], "top.il")
            self.assertEqual(manifest["pins_lock_file"], "pins.lock")

            mac = manifest["macros"]
            self.assertEqual(set(mac.keys()), {"sram", "pll"})
            self.assertEqual(mac["sram"]["name"], "SRAM_64X64")
            self.assertEqual(mac["sram"]["lef_file"], "macros/sram/SRAM_64X64.lef")
            self.assertEqual(mac["sram"]["frame_gds_file"], "macros/sram/SRAM_64X64.gds")
            self.assertEqual(
                mac["sram"]["blackbox_json_file"],
                "macros/sram/SRAM_64X64.blackbox.json",
            )
            # All macro file-pointing keys carry _file suffix so backend's
            # `_bundle_files_from_manifest` extractor finds them.
            for key in mac["sram"]:
                if key == "name":
                    continue
                self.assertTrue(key.endswith("_file"), f"{key} must end in _file")


if __name__ == "__main__":
    unittest.main()
