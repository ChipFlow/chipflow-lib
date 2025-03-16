# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest
from unittest import mock
import json
import tempfile
from pathlib import Path

import pytest

from chipflow_lib import ChipFlowError
from chipflow_lib.pin_lock import (
    count_member_pins,
    allocate_pins
)


class TestPinLock(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        
        # Mock environment for testing
        self.chipflow_root_patcher = mock.patch.dict(os.environ, {"CHIPFLOW_ROOT": self.temp_dir.name})
        self.chipflow_root_patcher.start()

    def tearDown(self):
        self.chipflow_root_patcher.stop()
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    def test_count_member_pins_interface_with_annotation(self):
        """Test count_member_pins with an interface that has annotation"""
        PIN_ANNOTATION_SCHEMA = "https://api.chipflow.com/schemas/0/pin-annotation"
        member_data = {
            "type": "interface",
            "annotations": {
                PIN_ANNOTATION_SCHEMA: {
                    "width": 8
                }
            }
        }
        result = count_member_pins("test_interface", member_data)
        self.assertEqual(result, 8)

    def test_count_member_pins_interface_without_annotation(self):
        """Test count_member_pins with an interface that has no annotation"""
        member_data = {
            "type": "interface",
            "members": {
                "sub1": {
                    "type": "port",
                    "width": 4
                },
                "sub2": {
                    "type": "port",
                    "width": 6
                }
            }
        }
        result = count_member_pins("test_interface", member_data)
        self.assertEqual(result, 10)  # 4 + 6

    def test_count_member_pins_port(self):
        """Test count_member_pins with a direct port"""
        member_data = {
            "type": "port",
            "width": 16
        }
        result = count_member_pins("test_port", member_data)
        self.assertEqual(result, 16)

    def test_allocate_pins_interface_with_annotation(self):
        """Test allocate_pins with an interface that has annotation"""
        PIN_ANNOTATION_SCHEMA = "https://api.chipflow.com/schemas/0/pin-annotation"
        member_data = {
            "type": "interface",
            "annotations": {
                PIN_ANNOTATION_SCHEMA: {
                    "width": 4,
                    "direction": "io",
                    "options": {"all_have_oe": True}
                }
            }
        }
        pins = ["pin1", "pin2", "pin3", "pin4", "pin5", "pin6"]
        
        pin_map, remaining_pins = allocate_pins("test_interface", member_data, pins)
        
        # Check that correct pins were allocated
        self.assertIn("test_interface", pin_map)
        self.assertEqual(pin_map["test_interface"]["pins"], pins[:4])
        self.assertEqual(pin_map["test_interface"]["direction"], "io")
        
        # Check remaining pins
        self.assertEqual(remaining_pins, pins[4:])

    def test_allocate_pins_interface_without_annotation(self):
        """Test allocate_pins with an interface that has no annotation"""
        member_data = {
            "type": "interface",
            "members": {
                "sub1": {
                    "type": "port",
                    "width": 2,
                    "dir": "i"
                },
                "sub2": {
                    "type": "port",
                    "width": 3,
                    "dir": "o"
                }
            }
        }
        pins = ["pin1", "pin2", "pin3", "pin4", "pin5", "pin6"]
        
        pin_map, remaining_pins = allocate_pins("test_interface", member_data, pins)
        
        # Check that correct pins were allocated
        self.assertIn("sub1", pin_map)
        self.assertEqual(pin_map["sub1"]["pins"], pins[:2])
        self.assertEqual(pin_map["sub1"]["direction"], "i")
        
        self.assertIn("sub2", pin_map)
        self.assertEqual(pin_map["sub2"]["pins"], pins[2:5])
        self.assertEqual(pin_map["sub2"]["direction"], "o")
        
        # Check remaining pins
        self.assertEqual(remaining_pins, pins[5:])

    def test_allocate_pins_port(self):
        """Test allocate_pins with a direct port"""
        member_data = {
            "type": "port",
            "width": 3,
            "dir": "i"
        }
        pins = ["pin1", "pin2", "pin3", "pin4"]
        
        pin_map, remaining_pins = allocate_pins("test_port", member_data, pins, port_name="my_port")
        
        # Check that correct pins were allocated
        self.assertIn("test_port", pin_map)
        self.assertEqual(pin_map["test_port"]["pins"], pins[:3])
        self.assertEqual(pin_map["test_port"]["direction"], "i")
        self.assertEqual(pin_map["test_port"]["port_name"], "my_port")
        
        # Check remaining pins
        self.assertEqual(remaining_pins, pins[3:])

    @mock.patch("chipflow_lib.pin_lock.lock_pins")
    def test_pin_command_mocked(self, mock_lock_pins):
        """Test pin_command via mocking"""
        # Import here to avoid import issues during test collection
        from chipflow_lib.pin_lock import PinCommand
        
        # Create mock config
        mock_config = {"test": "config"}
        
        # Create command instance
        cmd = PinCommand(mock_config)
        
        # Create mock args
        mock_args = mock.Mock()
        mock_args.action = "lock"
        
        # Call run_cli
        cmd.run_cli(mock_args)
        
        # Verify lock_pins was called
        mock_lock_pins.assert_called_once()
        
        # Test build_cli_parser
        mock_parser = mock.Mock()
        mock_subparsers = mock.Mock()
        mock_parser.add_subparsers.return_value = mock_subparsers
        
        cmd.build_cli_parser(mock_parser)
        
        # Verify parser was built
        mock_parser.add_subparsers.assert_called_once()
        mock_subparsers.add_parser.assert_called_once()