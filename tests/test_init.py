# SPDX-License-Identifier: BSD-2-Clause
import os
import sys
import unittest
import tempfile

from pathlib import Path
from unittest import mock

from chipflow_lib import (
    ChipFlowError,
    _get_cls_by_reference,
    _ensure_chipflow_root,
    _parse_config
)
from chipflow_lib.config import _parse_config_file
from chipflow_lib.config_models import Config, ChipFlowConfig
from chipflow_lib.platforms import Process


class TestCoreUtilities(unittest.TestCase):
    def setUp(self):
        # Save original environment to restore later
        self.original_chipflow_root = os.environ.get("CHIPFLOW_ROOT")
        self.original_sys_path = sys.path.copy()

        # Create a temporary directory for tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = self.temp_dir.name

    def tearDown(self):
        # Restore original environment
        if self.original_chipflow_root:
            os.environ["CHIPFLOW_ROOT"] = self.original_chipflow_root
        else:
            os.environ.pop("CHIPFLOW_ROOT", None)

        sys.path = self.original_sys_path
        self.temp_dir.cleanup()

    def test_chipflow_error(self):
        """Test that ChipFlowError can be raised and caught properly"""
        with self.assertRaises(ChipFlowError):
            raise ChipFlowError("Test error")

    def test_get_cls_by_reference_valid(self):
        """Test retrieving a class by reference when the module and class exist"""
        # unittest.TestCase is a valid class that should be importable
        cls = _get_cls_by_reference("unittest:TestCase", "test context")
        self.assertEqual(cls, unittest.TestCase)

    def test_get_cls_by_reference_module_not_found(self):
        """Test _get_cls_by_reference when the module doesn't exist"""
        with self.assertRaises(ChipFlowError) as cm:
            _get_cls_by_reference("nonexistent_module:SomeClass", "test context")

        self.assertIn("Module `nonexistent_module` referenced by test context is not found", str(cm.exception))

    def test_get_cls_by_reference_class_not_found(self):
        """Test _get_cls_by_reference when the class doesn't exist in the module"""
        with self.assertRaises(ChipFlowError) as cm:
            _get_cls_by_reference("unittest:NonExistentClass", "test context")

        self.assertIn("Module `unittest` referenced by test context does not define `NonExistentClass`", str(cm.exception))

    def test_ensure_chipflow_root_already_set(self):
        """Test _ensure_chipflow_root when CHIPFLOW_ROOT is already set"""
        os.environ["CHIPFLOW_ROOT"] = "/test/path"
        sys.path = ["/some/other/path"]

        _ensure_chipflow_root.root = None  #type: ignore
        result = _ensure_chipflow_root()

        self.assertEqual(result, Path("/test/path"))
        self.assertIn("/test/path", sys.path)

    def test_ensure_chipflow_root_not_set(self):
        """Test _ensure_chipflow_root when CHIPFLOW_ROOT is not set"""
        if "CHIPFLOW_ROOT" in os.environ:
            del os.environ["CHIPFLOW_ROOT"]
        _ensure_chipflow_root.root = None  #type: ignore

        with mock.patch("os.getcwd", return_value="/mock/cwd"):
            result = _ensure_chipflow_root()

            self.assertEqual(result, Path("/mock/cwd"))
            self.assertEqual(os.environ["CHIPFLOW_ROOT"], "/mock/cwd")
            self.assertIn("/mock/cwd", sys.path)

    def test_parse_config_file_valid(self):
        """Test _parse_config_file with a valid config file"""
        # Create a temporary config file
        config_content = """
[chipflow]
project_name = "test_project"
steps = { silicon = "chipflow_lib.steps.silicon:SiliconStep" }
clocks = { default = "sys_clk" }
resets = { default = "sys_rst_n" }

[chipflow.silicon]
process = "sky130"
package = "caravel"
"""
        config_path = os.path.join(self.temp_path, "chipflow.toml")
        with open(config_path, "w") as f:
            f.write(config_content)

        config = _parse_config_file(config_path)

        assert config.chipflow
        assert config.chipflow.silicon
        self.assertEqual(config.chipflow.project_name, "test_project")
        self.assertEqual(config.chipflow.silicon.process, Process.SKY130)

    @mock.patch("chipflow_lib._ensure_chipflow_root")
    @mock.patch("chipflow_lib.config._parse_config_file")
    def test_parse_config(self, mock_parse_config_file, mock_ensure_chipflow_root):
        """Test _parse_config which uses _ensure_chipflow_root and _parse_config_file"""
        mock_ensure_chipflow_root.return_value = "/mock/chipflow/root"
        mock_parse_config_file.return_value = Config(chipflow=ChipFlowConfig(project_name='test', top={'test': 'test'}))

        config = _parse_config()

        mock_ensure_chipflow_root.assert_called_once()
        # Accept either string or Path object
        self.assertEqual(mock_parse_config_file.call_args[0][0].as_posix()
                        if hasattr(mock_parse_config_file.call_args[0][0], 'as_posix')
                        else mock_parse_config_file.call_args[0][0],
                        "/mock/chipflow/root/chipflow.toml")
        self.assertEqual(config.chipflow.project_name, "test")
        self.assertEqual(config.chipflow.top, {'test': 'test'})
