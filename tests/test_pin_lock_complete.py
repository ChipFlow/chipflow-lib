# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest
from unittest import mock
import tempfile
import json
from pathlib import Path
from io import StringIO
from pprint import pformat

from chipflow_lib import ChipFlowError
from chipflow_lib.pin_lock import (
    lock_pins,
    count_member_pins,
    allocate_pins,
    PinCommand
)


class MockPackageType:
    """Mock for package type class used in tests"""
    def __init__(self, name="test_package"):
        self.name = name
        self.pins = set([str(i) for i in range(1, 100)])  # Create pins 1-99
        self.allocated_pins = []
    
    def sortpins(self, pins):
        return sorted(list(pins))
    
    def allocate(self, available, width):
        # Simple allocation - just return the first 'width' pins from available
        available_list = sorted(list(available))
        allocated = available_list[:width]
        self.allocated_pins.append(allocated)
        return allocated




class TestPinLockUtilities(unittest.TestCase):
    """Tests for utility functions in pin_lock module"""
    
    def test_allocate_pins_with_pin_signature(self):
        """Test allocate_pins with PinSignature annotation"""
        PIN_ANNOTATION_SCHEMA = "https://api.chipflow.com/schemas/0/pin-annotation"
        
        # Create member data with annotation
        member_data = {
            "type": "interface",
            "annotations": {
                PIN_ANNOTATION_SCHEMA: {
                    "width": 3,
                    "direction": "o",
                    "options": {"opt1": "val1"}
                }
            }
        }
        
        pins = ["pin1", "pin2", "pin3", "pin4", "pin5"]
        port_name = "test_port"
        
        # Call allocate_pins
        pin_map, remaining = allocate_pins("output_port", member_data, pins, port_name)
        
        # Check results
        self.assertIn("output_port", pin_map)
        self.assertEqual(pin_map["output_port"]["pins"], pins[:3])
        self.assertEqual(pin_map["output_port"]["direction"], "o")
        self.assertEqual(pin_map["output_port"]["type"], "io")
        self.assertEqual(pin_map["output_port"]["port_name"], "test_port")
        self.assertEqual(pin_map["output_port"]["options"], {"opt1": "val1"})
        
        # Check remaining pins
        self.assertEqual(remaining, pins[3:])

    def test_allocate_pins_nested_interface(self):
        """Test allocate_pins with nested interfaces"""
        # Create nested member data
        member_data = {
            "type": "interface",
            "members": {
                "uart_tx": {
                    "type": "port",
                    "width": 1,
                    "dir": "o"
                },
                "uart_rx": {
                    "type": "port",
                    "width": 1,
                    "dir": "i"
                }
            }
        }
        
        pins = ["pin1", "pin2", "pin3", "pin4"]
        
        # Call allocate_pins
        pin_map, remaining = allocate_pins("uart", member_data, pins)
        
        # Check results
        self.assertIn("uart_tx", pin_map)
        self.assertEqual(pin_map["uart_tx"]["pins"], ["pin1"])
        self.assertEqual(pin_map["uart_tx"]["direction"], "o")
        
        self.assertIn("uart_rx", pin_map)
        self.assertEqual(pin_map["uart_rx"]["pins"], ["pin2"])
        self.assertEqual(pin_map["uart_rx"]["direction"], "i")
        
        # Check remaining pins
        self.assertEqual(remaining, pins[2:])

    def test_count_member_pins_with_annotation(self):
        """Test count_member_pins with PinSignature annotation"""
        PIN_ANNOTATION_SCHEMA = "https://api.chipflow.com/schemas/0/pin-annotation"
        
        # Create member data with annotation
        member_data = {
            "type": "interface",
            "annotations": {
                PIN_ANNOTATION_SCHEMA: {
                    "width": 8
                }
            }
        }
        
        # Call count_member_pins
        count = count_member_pins("test_port", member_data)
        
        # Check result
        self.assertEqual(count, 8)

    def test_count_member_pins_nested_interface(self):
        """Test count_member_pins with nested interfaces"""
        # Create nested member data
        member_data = {
            "type": "interface",
            "members": {
                "port1": {
                    "type": "port",
                    "width": 4
                },
                "port2": {
                    "type": "port",
                    "width": 2
                }
            }
        }
        
        # Call count_member_pins
        count = count_member_pins("test_interface", member_data)
        
        # Check result
        self.assertEqual(count, 6)  # 4 + 2