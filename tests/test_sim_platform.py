# amaranth: UnusedElaboratable=no
# SPDX-License-Identifier: BSD-2-Clause

import os
import unittest
from unittest import mock
from pathlib import Path

import tomli
from amaranth import Module, Signal, Cat, ClockDomain, Shape
from amaranth.lib import io
from amaranth.hdl import Instance

from chipflow_lib import ChipFlowError


class TestSimPlatform(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Set up environment variable
        self.original_chipflow_root = os.environ.get("CHIPFLOW_ROOT")
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))
        
        # Load config for use in tests
        current_dir = os.path.dirname(__file__)
        customer_config = f"{current_dir}/fixtures/mock.toml"
        with open(customer_config, "rb") as f:
            self.config = tomli.load(f)

    def tearDown(self):
        """Clean up environment"""
        if self.original_chipflow_root:
            os.environ["CHIPFLOW_ROOT"] = self.original_chipflow_root
        else:
            os.environ.pop("CHIPFLOW_ROOT", None)

    def test_sim_platform_init(self):
        """Test SimPlatform initialization"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.sim import SimPlatform
        
        # Create platform
        platform = SimPlatform()
        
        # Check initialization
        self.assertEqual(platform.build_dir, os.path.join(os.environ['CHIPFLOW_ROOT'], 'build', 'sim'))
        self.assertEqual(platform.extra_files, {})
        self.assertEqual(platform.sim_boxes, {})
        
        # Check signals
        self.assertIsInstance(platform.clk, Signal)
        self.assertIsInstance(platform.rst, Signal)
        self.assertIsInstance(platform.buttons, Signal)
        self.assertEqual(len(platform.buttons), 2)

    def test_add_file(self):
        """Test add_file method"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.sim import SimPlatform
        
        # Create platform
        platform = SimPlatform()
        
        # Test with string content
        platform.add_file("test.v", "module test(); endmodule")
        self.assertIn("test.v", platform.extra_files)
        self.assertEqual(platform.extra_files["test.v"], "module test(); endmodule")
        
        # Test with file-like object
        file_obj = mock.Mock()
        file_obj.read.return_value = "module test2(); endmodule"
        platform.add_file("test2.v", file_obj)
        self.assertIn("test2.v", platform.extra_files)
        self.assertEqual(platform.extra_files["test2.v"], "module test2(); endmodule")
        
    @mock.patch('chipflow_lib.platforms.sim.ClockSignal')
    def test_add_model(self, mock_clock_signal):
        """Test add_model method"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.sim import SimPlatform
        
        # Create platform
        platform = SimPlatform()
        
        # Create mock clock signal
        mock_clock = Signal()
        mock_clock_signal.return_value = mock_clock
        
        # Create mock interface with signature
        mock_iface = mock.MagicMock()
        mock_iface.signature = mock.MagicMock()
        mock_iface.signature.members = ["data_o", "valid_oe", "ready_i"]
        
        # Create mock signals for interface members
        mock_iface.data_o = Signal(8)
        mock_iface.valid_oe = Signal()
        mock_iface.ready_i = Signal()
        
        # Mock the signature flatten method
        mock_flatten_result = [
            (("data_o",), None, mock_iface.data_o),
            (("valid_oe",), None, mock_iface.valid_oe),
            (("ready_i",), None, mock_iface.ready_i)
        ]
        mock_iface.signature.flatten.return_value = mock_flatten_result
        
        # Call add_model
        result = platform.add_model("test_model", mock_iface)
        
        # Check result is an Instance with the correct name
        self.assertIsInstance(result, Instance)
        self.assertEqual(result.type, "test_model")
        
        # Check sim_boxes was populated with the blackbox definition
        self.assertIn("test_model", platform.sim_boxes)
        blackbox = platform.sim_boxes["test_model"]
        self.assertIn("module \\test_model", blackbox)
        self.assertIn("wire width 1 input 0 \\clk", blackbox)
        self.assertIn("wire width 8 input 0 \\data_o", blackbox)  
        self.assertIn("wire width 1 input 1 \\valid_oe", blackbox)
        self.assertIn("wire width 1 output 2 \\ready_i", blackbox)
        
    @mock.patch('chipflow_lib.platforms.sim.ClockSignal')
    def test_add_model_with_edge_detection(self, mock_clock_signal):
        """Test add_model method with edge detection"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.sim import SimPlatform
        
        # Create platform
        platform = SimPlatform()
        
        # Create mock clock signal
        mock_clock = Signal()
        mock_clock_signal.return_value = mock_clock
        
        # Create mock interface with signature
        mock_iface = mock.MagicMock()
        mock_iface.signature = mock.MagicMock()
        mock_iface.signature.members = ["data_o", "valid_oe", "ready_i"]
        
        # Create mock signals for interface members
        mock_iface.data_o = Signal(8)
        mock_iface.valid_oe = Signal()
        mock_iface.ready_i = Signal()
        
        # Mock the signature flatten method
        mock_flatten_result = [
            (("data_o",), None, mock_iface.data_o),
            (("valid_oe",), None, mock_iface.valid_oe),
            (("ready_i",), None, mock_iface.ready_i)
        ]
        mock_iface.signature.flatten.return_value = mock_flatten_result
        
        # Call add_model with edge detection for ready_i
        edge_detect = ["ready_i"]
        result = platform.add_model("test_model_edge", mock_iface, edge_det=edge_detect)
        
        # Check result is an Instance with the correct name
        self.assertIsInstance(result, Instance)
        self.assertEqual(result.type, "test_model_edge")
        
        # Check sim_boxes was populated with the blackbox definition including edge detection
        self.assertIn("test_model_edge", platform.sim_boxes)
        blackbox = platform.sim_boxes["test_model_edge"]
        
        # Check for edge detection attribute
        self.assertIn("attribute \\cxxrtl_edge \"a\"", blackbox)
        
        # Check that the ready_i signal has the edge detection attribute applied
        # Note: the attribute appears right before the wire definition for ready_i
        ready_wire_pos = blackbox.find("wire width 1 output") 
        ready_attr_pos = blackbox.rfind("attribute \\cxxrtl_edge \"a\"", 0, ready_wire_pos)
        self.assertTrue(ready_attr_pos > 0, "Edge detection attribute not found for ready_i")
        
    @mock.patch('chipflow_lib.platforms.sim.ClockSignal')
    def test_add_monitor(self, mock_clock_signal):
        """Test add_monitor method"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.sim import SimPlatform
        
        # Create platform
        platform = SimPlatform()
        
        # Create mock clock signal
        mock_clock = Signal()
        mock_clock_signal.return_value = mock_clock
        
        # Create mock interface with signature
        mock_iface = mock.MagicMock()
        mock_iface.signature = mock.MagicMock()
        mock_iface.signature.members = ["data", "valid", "ready"]
        
        # Create mock signals for interface members
        mock_iface.data = Signal(8)
        mock_iface.valid = Signal()
        mock_iface.ready = Signal()
        
        # Mock the signature flatten method
        mock_flatten_result = [
            (("data",), None, mock_iface.data),
            (("valid",), None, mock_iface.valid),
            (("ready",), None, mock_iface.ready)
        ]
        mock_iface.signature.flatten.return_value = mock_flatten_result
        
        # Call add_monitor
        result = platform.add_monitor("test_monitor", mock_iface)
        
        # Check result is an Instance with the correct name
        self.assertIsInstance(result, Instance)
        self.assertEqual(result.type, "test_monitor")
        
        # Check sim_boxes was populated with the blackbox definition
        self.assertIn("test_monitor", platform.sim_boxes)
        blackbox = platform.sim_boxes["test_monitor"]
        self.assertIn("module \\test_monitor", blackbox)
        self.assertIn("wire width 1 input 0 \\clk", blackbox)
        self.assertIn("wire width 8 input 1 \\data", blackbox)  
        self.assertIn("wire width 1 input 2 \\valid", blackbox)
        self.assertIn("wire width 1 input 3 \\ready", blackbox)
        
    @mock.patch('pathlib.Path.mkdir')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('chipflow_lib.platforms.sim.rtlil.convert')
    def test_build(self, mock_convert, mock_open, mock_mkdir):
        """Test build method"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.sim import SimPlatform
        
        # Create platform
        platform = SimPlatform()
        
        # Add some sim boxes
        platform.sim_boxes = {
            "model1": "module \\model1\nend\n",
            "model2": "module \\model2\nend\n"
        }
        
        # Add some extra files
        platform.extra_files = {
            "extra.v": "module extra(); endmodule",
            "extra.il": "module \\extra\nend\n"
        }
        
        # Mock convert result
        mock_convert.return_value = "# Converted RTL output"
        
        # Create mock module
        mock_module = Module()
        
        # Call build
        platform.build(mock_module)
        
        # Check directory was created
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        
        # Check convert was called with right parameters
        mock_convert.assert_called_once_with(
            mock_module, 
            name="sim_top", 
            ports=[platform.clk, platform.rst, platform.buttons], 
            platform=platform
        )
        
        # Check that the open function was called to write the files
        self.assertTrue(mock_open.called, "Open was not called")
        
        # Since we're mocking the open() function which is used with "with" statements,
        # the actual file content doesn't matter for our test. We just need to verify
        # that open was called with the correct file paths and mode.
        
        # Extract all file paths that were opened with 'w' mode
        opened_files = [args[0][0] for args in mock_open.call_args_list]
        
        # Expected files
        rtlil_path = str(Path(platform.build_dir) / "sim_soc.il")
        ys_path = str(Path(platform.build_dir) / "sim_soc.ys")
        extra_v_path = str(Path(platform.build_dir) / "extra.v")
        extra_il_path = str(Path(platform.build_dir) / "extra.il")
        
        # Check if all expected files were opened
        expected_files = [rtlil_path, ys_path, extra_v_path, extra_il_path]
        
        # The files might be opened in any order, so we just check if all expected files
        # were opened at some point
        for expected_file in expected_files:
            # Check if the file path or a file path that ends with the expected file exists in the list
            # This handles differences in how Path objects are represented
            found = False
            for opened_file in opened_files:
                if str(opened_file) == expected_file or str(opened_file).endswith(expected_file.split('/')[-1]):
                    found = True
                    break
            self.assertTrue(found, f"Expected file {expected_file} was not opened")