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
from chipflow.config.parser import _parse_config_file
from chipflow.config_models import Config, ChipFlowConfig
# Process is not part of the public API, so we won't test it here


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

        # Check that error message contains key information
        error_msg = str(cm.exception)
        self.assertIn("nonexistent_module", error_msg)
        self.assertIn("not found", error_msg.lower())

    def test_get_cls_by_reference_class_not_found(self):
        """Test _get_cls_by_reference when the class doesn't exist in the module"""
        with self.assertRaises(ChipFlowError) as cm:
            _get_cls_by_reference("unittest:NonExistentClass", "test context")

        # Check that error message contains key information
        error_msg = str(cm.exception)
        self.assertIn("NonExistentClass", error_msg)
        self.assertIn("unittest", error_msg)
        self.assertIn("not found", error_msg.lower())

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
        # Process enum is not part of the public API, so we just check that process has a string value
        self.assertEqual(str(config.chipflow.silicon.process), "sky130")

    @mock.patch("chipflow.config.parser.ensure_chipflow_root")
    @mock.patch("chipflow.config.parser._parse_config_file")
    def test_parse_config(self, mock_parse_config_file, mock_ensure_chipflow_root):
        """Test _parse_config which uses ensure_chipflow_root and _parse_config_file"""
        mock_ensure_chipflow_root.return_value = Path("/mock/chipflow/root")
        mock_parse_config_file.return_value = Config(chipflow=ChipFlowConfig(project_name='test', top={'test': 'test'}))

        config = _parse_config()

        # Note: ensure_chipflow_root may or may not be called depending on caching
        # Just verify that _parse_config_file was called with the correct path
        self.assertTrue(mock_parse_config_file.called)
        # Accept either string or Path object
        called_path = mock_parse_config_file.call_args[0][0]
        actual_path = called_path.as_posix() if hasattr(called_path, 'as_posix') else str(called_path)
        self.assertIn("chipflow.toml", actual_path)
        self.assertEqual(config.chipflow.project_name, "test")
        self.assertEqual(config.chipflow.top, {'test': 'test'})
