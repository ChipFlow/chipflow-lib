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


@mock.patch('chipflow_lib.pin_lock._parse_config')
class TestLockPins(unittest.TestCase):
    def setUp(self):
        """Set up test environment with temporary directory"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)

        # Set up mock environment variables
        self.env_patcher = mock.patch.dict(os.environ, {
            "CHIPFLOW_ROOT": self.temp_dir.name
        })
        self.env_patcher.start()

        # Create test configuration
        self.test_config = {
            "chipflow": {
                "silicon": {
                    "package": "test_package",
                    "pads": {
                        "clk": {"type": "clock", "loc": "1"},
                        "rst": {"type": "reset", "loc": "2"},
                        "led": {"type": "io", "loc": "3"}
                    },
                    "power": {
                        "vdd": {"type": "power", "loc": "4"},
                        "vss": {"type": "ground", "loc": "5"}
                    }
                },
                "clocks": {
                    "default": "clk"
                },
                "resets": {
                    "default": "rst"
                },
                "top": {
                    "soc": "module:SoC"
                }
            }
        }

        # Create mock interfaces
        self.mock_interfaces = {
            "soc": {
                "interface": {
                    "members": {
                        "uart": {
                            "type": "interface",
                            "members": {
                                "tx": {"type": "port", "width": 1, "dir": "o"},
                                "rx": {"type": "port", "width": 1, "dir": "i"}
                            }
                        },
                        "gpio": {
                            "type": "interface",
                            "members": {
                                "pins": {"type": "port", "width": 4, "dir": "io"}
                            }
                        }
                    }
                }
            }
        }

    def tearDown(self):
        """Clean up after tests"""
        self.env_patcher.stop()
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    @mock.patch('chipflow_lib.pin_lock.PACKAGE_DEFINITIONS')
    @mock.patch('chipflow_lib.pin_lock.top_interfaces')
    @mock.patch('builtins.print')
    def test_lock_pins_new_lockfile(self, mock_print, mock_top_interfaces, mock_package_defs, mock_parse_config):
        """Test lock_pins when no lockfile exists"""
        # Setup mocks
        mock_parse_config.return_value = self.test_config
        mock_top_interfaces.return_value = ({}, self.mock_interfaces)

        # Create mock package type
        mock_package_type = MockPackageType()
        mock_package_defs.__getitem__.return_value = mock_package_type
        mock_package_defs.__contains__.return_value = True

        # Execute lock_pins
        with mock.patch('chipflow_lib.pin_lock.logger') as mock_logger:
            lock_pins()

        # Verify print and logger calls
        mock_print.assert_called_once_with("Locking pins: ")
        mock_logger.debug.assert_any_call(f"Checking [chipflow.silicon.pads]:")
        mock_logger.debug.assert_any_call(f"Checking [chipflow.silicon.power]:")

        # Verify lockfile was created
        lockfile_path = Path('pins.lock')
        self.assertTrue(lockfile_path.exists())

        # Check content of lockfile
        with open(lockfile_path, 'r') as f:
            lock_data = json.load(f)

        # Check that pins were allocated for interfaces
        self.assertIn("port_map", lock_data)
        self.assertIn("soc", lock_data["port_map"])
        self.assertIn("uart", lock_data["port_map"]["soc"])
        self.assertIn("gpio", lock_data["port_map"]["soc"])

        # Check that pin allocations make sense
        self.assertEqual(len(lock_data["port_map"]["soc"]["uart"]["tx"]["pins"]), 1)
        self.assertEqual(len(lock_data["port_map"]["soc"]["uart"]["rx"]["pins"]), 1)
        self.assertEqual(len(lock_data["port_map"]["soc"]["gpio"]["pins"]["pins"]), 4)

    @mock.patch('chipflow_lib.pin_lock.PACKAGE_DEFINITIONS')
    @mock.patch('chipflow_lib.pin_lock.top_interfaces')
    @mock.patch('builtins.print')
    def test_lock_pins_existing_lockfile(self, mock_print, mock_top_interfaces, mock_package_defs, mock_parse_config):
        """Test lock_pins when lockfile exists"""
        # Setup mocks
        mock_parse_config.return_value = self.test_config
        mock_top_interfaces.return_value = ({}, self.mock_interfaces)

        # Create mock package type
        mock_package_type = MockPackageType()
        mock_package_defs.__getitem__.return_value = mock_package_type
        mock_package_defs.__contains__.return_value = True

        # Create existing lockfile with predefined pin allocations
        existing_lock = {
            "package": {
                "package_type": {
                    "type": "_QuadPackageDef",
                    "name": "test_package",
                    "width": 36,
                    "height": 36
                },
                "power": {
                    "vdd": {"type": "power", "pins": ["4"], "port_name": "vdd"},
                    "vss": {"type": "ground", "pins": ["5"], "port_name": "vss"}
                },
                "clocks": {
                    "clk": {"type": "clock", "pins": ["1"], "direction": "i", "port_name": "clk"}
                },
                "resets": {
                    "rst": {"type": "reset", "pins": ["2"], "direction": "i", "port_name": "rst"}
                }
            },
            "port_map": {
                "soc": {
                    "uart": {
                        "tx": {"type": "output", "pins": ["10"], "port_name": "soc_uart_tx", "direction": "o"},
                        "rx": {"type": "input", "pins": ["11"], "port_name": "soc_uart_rx", "direction": "i"}
                    },
                    "gpio": {
                        "pins": {"type": "bidir", "pins": ["12", "13", "14", "15"], "port_name": "soc_gpio_pins", "direction": "io"}
                    }
                }
            },
            "metadata": self.mock_interfaces
        }

        with open('pins.lock', 'w') as f:
            json.dump(existing_lock, f)

        # Execute lock_pins
        with mock.patch('chipflow_lib.pin_lock.logger') as mock_logger:
            lock_pins()

        # Verify print and logger calls
        mock_print.assert_called_once_with("Locking pins: using pins.lock")

        # Verify lockfile was updated
        lockfile_path = Path('pins.lock')
        self.assertTrue(lockfile_path.exists())

        # Check content of lockfile
        with open(lockfile_path, 'r') as f:
            lock_data = json.load(f)

        # Check that pins were preserved from existing lock
        self.assertEqual(lock_data["port_map"]["soc"]["uart"]["tx"]["pins"], ["10"])
        self.assertEqual(lock_data["port_map"]["soc"]["uart"]["rx"]["pins"], ["11"])
        self.assertEqual(lock_data["port_map"]["soc"]["gpio"]["pins"]["pins"], ["12", "13", "14", "15"])

    @mock.patch('chipflow_lib.pin_lock.PACKAGE_DEFINITIONS')
    @mock.patch('chipflow_lib.pin_lock.top_interfaces')
    def test_lock_pins_out_of_pins(self, mock_top_interfaces, mock_package_defs, mock_parse_config):
        """Test lock_pins when we run out of pins"""
        # Setup mocks
        mock_parse_config.return_value = self.test_config
        mock_top_interfaces.return_value = ({}, self.mock_interfaces)

        # Create mock package type with limited pins
        limited_package = MockPackageType()
        limited_package.pins = set(["1", "2", "3", "4", "5"])  # Only enough for the fixed pins
        mock_package_defs.__getitem__.return_value = limited_package
        mock_package_defs.__contains__.return_value = True

        # Execute lock_pins - should raise an error
        with self.assertRaises(ChipFlowError) as cm:
            lock_pins()

        self.assertIn("No pins were allocated", str(cm.exception))

    @mock.patch('chipflow_lib.pin_lock.PACKAGE_DEFINITIONS')
    @mock.patch('chipflow_lib.pin_lock.top_interfaces')
    def test_lock_pins_pin_conflict(self, mock_top_interfaces, mock_package_defs, mock_parse_config):
        """Test lock_pins when there's a pin conflict with existing lock"""
        # Setup mocks
        # Change the loc of a pin in the config
        conflicting_config = self.test_config.copy()
        conflicting_config["chipflow"]["silicon"]["pads"]["clk"]["loc"] = "99"

        mock_parse_config.return_value = conflicting_config
        mock_top_interfaces.return_value = ({}, self.mock_interfaces)

        # Create mock package type
        mock_package_type = MockPackageType()
        mock_package_defs.__getitem__.return_value = mock_package_type
        mock_package_defs.__contains__.return_value = True

        # Create existing lockfile with clk on pin 1
        existing_lock = {
            "package": {
                "package_type": {
                    "type": "_QuadPackageDef",
                    "name": "test_package",
                    "width": 36,
                    "height": 36
                },
                "power": {
                    "vdd": {"type": "power", "pins": ["4"], "port_name": "vdd"},
                    "vss": {"type": "ground", "pins": ["5"], "port_name": "vss"}
                },
                "clocks": {
                    "clk": {"type": "clock", "pins": ["1"], "direction": "i", "port_name": "clk"}
                },
                "resets": {
                    "rst": {"type": "reset", "pins": ["2"], "direction": "i", "port_name": "rst"}
                }
            },
            "port_map": {},
            "metadata": {}
        }

        with open('pins.lock', 'w') as f:
            json.dump(existing_lock, f)

        # Execute lock_pins - should raise an error
        with self.assertRaises(ChipFlowError) as cm:
            lock_pins()

        self.assertIn("conflicts with pins.lock", str(cm.exception))

    @mock.patch('chipflow_lib.pin_lock.PACKAGE_DEFINITIONS')
    @mock.patch('chipflow_lib.pin_lock.top_interfaces')
    def test_lock_pins_interface_size_change(self, mock_top_interfaces, mock_package_defs, mock_parse_config):
        """Test lock_pins when an interface changes size"""
        # Setup mocks
        mock_parse_config.return_value = self.test_config

        # Create interfaces with larger gpio width
        modified_interfaces = {
            "soc": {
                "interface": {
                    "members": {
                        "uart": {
                            "type": "interface",
                            "members": {
                                "tx": {"type": "port", "width": 1, "dir": "o"},
                                "rx": {"type": "port", "width": 1, "dir": "i"}
                            }
                        },
                        "gpio": {
                            "type": "interface",
                            "members": {
                                "pins": {"type": "port", "width": 8, "dir": "io"}  # Changed from 4 to 8
                            }
                        }
                    }
                }
            }
        }

        mock_top_interfaces.return_value = ({}, modified_interfaces)

        # Create mock package type
        mock_package_type = MockPackageType()
        mock_package_defs.__getitem__.return_value = mock_package_type
        mock_package_defs.__contains__.return_value = True

        # Create existing lockfile with gpio width 4
        existing_lock = {
            "package": {
                "package_type": {
                    "type": "_QuadPackageDef",
                    "name": "test_package",
                    "width": 36,
                    "height": 36
                },
                "power": {
                    "vdd": {"type": "power", "pins": ["4"], "port_name": "vdd"},
                    "vss": {"type": "ground", "pins": ["5"], "port_name": "vss"}
                },
                "clocks": {
                    "clk": {"type": "clock", "pins": ["1"], "direction": "i", "port_name": "clk"}
                },
                "resets": {
                    "rst": {"type": "reset", "pins": ["2"], "direction": "i", "port_name": "rst"}
                }
            },
            "port_map": {
                "soc": {
                    "uart": {
                        "tx": {"type": "output", "pins": ["10"], "port_name": "soc_uart_tx", "direction": "o"},
                        "rx": {"type": "input", "pins": ["11"], "port_name": "soc_uart_rx", "direction": "i"}
                    },
                    "gpio": {
                        "pins": {"type": "bidir", "pins": ["12", "13", "14", "15"], "port_name": "soc_gpio_pins", "direction": "io"}
                    }
                }
            },
            "metadata": {}
        }

        with open('pins.lock', 'w') as f:
            json.dump(existing_lock, f)

        # Execute lock_pins - should raise an error
        with self.assertRaises(ChipFlowError) as cm:
            lock_pins()

        self.assertIn("has changed size", str(cm.exception))

    @mock.patch('chipflow_lib.pin_lock.PACKAGE_DEFINITIONS')
    @mock.patch('chipflow_lib.pin_lock.top_interfaces')
    @mock.patch('builtins.print')
    def test_lock_pins_unknown_package(self, mock_print, mock_top_interfaces, mock_package_defs, mock_parse_config):
        """Test lock_pins with an unknown package"""
        # Setup config with unknown package
        unknown_config = self.test_config.copy()
        unknown_config["chipflow"]["silicon"]["package"] = "unknown_package"
        mock_parse_config.return_value = unknown_config

        # Create mock interfaces
        mock_top_interfaces.return_value = ({}, {})

        # Set up package defs
        mock_package_defs.__contains__.return_value = False

        # Execute lock_pins
        with mock.patch('chipflow_lib.pin_lock.logger') as mock_logger:
            with self.assertRaises(KeyError) as cm:
                lock_pins()

        # Verify logger warning
        mock_logger.debug.assert_any_call("Package 'unknown_package is unknown")


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