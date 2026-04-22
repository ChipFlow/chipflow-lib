# SPDX-License-Identifier: BSD-2-Clause
"""Tests for RTLWrapper parameter handling."""

import shutil
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from chipflow.rtl import wrapper as wrapper_mod
from chipflow.rtl.wrapper import (
    ExternalWrapConfig,
    Files,
    RTLWrapper,
    load_wrapper_from_toml,
)


def _make_config(parameters=None):
    """Build a minimal ExternalWrapConfig usable for RTLWrapper unit tests."""
    return ExternalWrapConfig(
        name="dummy_mod",
        files=Files(path=Path("/tmp/unused-for-unit-tests")),
        parameters=parameters or {},
    )


class ParameterMergeTestCase(unittest.TestCase):
    """Merge precedence between TOML ``[parameters]`` and Python kwarg."""

    def test_no_parameters(self):
        w = RTLWrapper(_make_config())
        self.assertEqual(w._parameters, {})

    def test_toml_defaults_only(self):
        w = RTLWrapper(_make_config(parameters={"WIDTH": 32, "DEPTH": 8}))
        self.assertEqual(w._parameters, {"WIDTH": 32, "DEPTH": 8})

    def test_kwarg_only(self):
        w = RTLWrapper(_make_config(), parameters={"WIDTH": 64})
        self.assertEqual(w._parameters, {"WIDTH": 64})

    def test_kwarg_overrides_toml(self):
        w = RTLWrapper(
            _make_config(parameters={"WIDTH": 32, "DEPTH": 8}),
            parameters={"WIDTH": 64},
        )
        self.assertEqual(w._parameters, {"WIDTH": 64, "DEPTH": 8})


class ElaborateEmitsParametersTestCase(unittest.TestCase):
    """elaborate() must emit merged parameters as ``p_<NAME>`` on ``Instance``."""

    def test_p_prefixed_kwargs(self):
        w = RTLWrapper(
            _make_config(parameters={"WIDTH": 32}),
            parameters={"DEPTH": 8},
        )

        captured = {}
        real_instance = wrapper_mod.Instance

        def fake_instance(name, **kwargs):
            captured["name"] = name
            captured["kwargs"] = kwargs
            return real_instance(name, **kwargs)

        with unittest.mock.patch.object(wrapper_mod, "Instance", fake_instance):
            w.elaborate(platform=None)

        self.assertEqual(captured["name"], "dummy_mod")
        self.assertEqual(captured["kwargs"].get("p_WIDTH"), 32)
        self.assertEqual(captured["kwargs"].get("p_DEPTH"), 8)

    def test_no_parameters_emits_no_p_kwargs(self):
        w = RTLWrapper(_make_config())

        captured = {}
        real_instance = wrapper_mod.Instance

        def fake_instance(name, **kwargs):
            captured["kwargs"] = kwargs
            return real_instance(name, **kwargs)

        with unittest.mock.patch.object(wrapper_mod, "Instance", fake_instance):
            w.elaborate(platform=None)

        p_kwargs = {k: v for k, v in captured["kwargs"].items() if k.startswith("p_")}
        self.assertEqual(p_kwargs, {})


class LoadFromTomlTestCase(unittest.TestCase):
    """``load_wrapper_from_toml`` must thread parameters through the merge."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        # A minimal Verilog file so `source_path.glob("**/*.v")` finds something.
        (self.tmpdir / "dummy_mod.v").write_text("module dummy_mod(); endmodule\n")
        self.toml_path = self.tmpdir / "wrapper.toml"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_toml(self, extra=""):
        self.toml_path.write_text(
            f'name = "dummy_mod"\n'
            f'[files]\n'
            f'path = "{self.tmpdir}"\n'
            + extra
        )

    def test_toml_parameters_only(self):
        self._write_toml("[parameters]\nWIDTH = 32\nDEPTH = 8\n")
        w = load_wrapper_from_toml(self.toml_path)
        self.assertEqual(w._parameters, {"WIDTH": 32, "DEPTH": 8})

    def test_kwarg_overrides_toml(self):
        self._write_toml("[parameters]\nWIDTH = 32\nDEPTH = 8\n")
        w = load_wrapper_from_toml(self.toml_path, parameters={"WIDTH": 64})
        self.assertEqual(w._parameters, {"WIDTH": 64, "DEPTH": 8})

    def test_kwarg_without_toml_table(self):
        self._write_toml()
        w = load_wrapper_from_toml(self.toml_path, parameters={"WIDTH": 64})
        self.assertEqual(w._parameters, {"WIDTH": 64})


if __name__ == "__main__":
    unittest.main()
