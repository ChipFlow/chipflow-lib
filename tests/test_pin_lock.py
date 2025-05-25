# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest
from unittest import mock
import tempfile


from chipflow_lib import ChipFlowError
from chipflow_lib.pin_lock import (
    count_member_pins,
    allocate_pins
)

# Define a MockPackageType for testing
class MockPackageType:
    """Mock for package type class used in tests"""
    def __init__(self, name="test_package"):
        self.name = name
        self.pins = set([str(i) for i in range(1, 100)])  # Create pins 1-99
        self.allocated_pins = []
        # Create a mock for the allocate method
        self.allocate = mock.MagicMock(side_effect=self._allocate)

    def sortpins(self, pins):
        return sorted(list(pins))

    def _allocate(self, available, width):
        # Simple allocation - just return the first 'width' pins from available
        available_list = sorted(list(available))
        allocated = available_list[:width]
        self.allocated_pins.append(allocated)
        return allocated


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

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("chipflow_lib.pin_lock._parse_config")
    @mock.patch("chipflow_lib.pin_lock.top_interfaces")
    @mock.patch("pathlib.Path.exists")
    @mock.patch("pathlib.Path.read_text")
    @mock.patch("chipflow_lib.pin_lock.PACKAGE_DEFINITIONS", new_callable=dict)
    @mock.patch("chipflow_lib.pin_lock.LockFile")
    def test_lock_pins_new_lockfile(self, mock_lock_file, mock_package_defs,
                                   mock_read_text, mock_exists, mock_top_interfaces,
                                   mock_parse_config, mock_open):
        """Test lock_pins function creating a new lockfile"""
        # Setup mock package definitions
        mock_package_type = MockPackageType(name="cf20")
        mock_package_defs["cf20"] = mock_package_type

        # Setup mocks
        mock_exists.return_value = False  # No existing pins.lock

        # Mock config
        mock_config = {
            "chipflow": {
                "project_name": "test",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "silicon": {
                    "process": "ihp_sg13g2",
                    "package": "cf20",
                    "pads": {
                        "clk": {"type": "clock", "loc": "1"},
                        "rst": {"type": "reset", "loc": "2"}
                    },
                    "power": {
                        "vdd": {"type": "power", "loc": "3"},
                        "gnd": {"type": "ground", "loc": "4"}
                    }
                }
            }
        }
        mock_parse_config.return_value = mock_config

        # Mock top_interfaces
        mock_interface = {
            "comp1": {
                "interface": {
                    "members": {
                        "uart": {
                            "type": "interface",
                            "members": {
                                "tx": {"type": "port", "width": 1, "dir": "o"},
                                "rx": {"type": "port", "width": 1, "dir": "i"}
                            }
                        }
                    }
                }
            }
        }
        mock_top_interfaces.return_value = (None, mock_interface)

        # Set up LockFile mock
        mock_lock_instance = mock.MagicMock()
        mock_lock_file.return_value = mock_lock_instance
        # Make model_dump_json return a valid JSON string
        mock_lock_instance.model_dump_json.return_value = '{"test": "json"}'

        # Import and run lock_pins
        from chipflow_lib.pin_lock import lock_pins

        # Mock the Package.__init__ to avoid validation errors
        with mock.patch("chipflow_lib.pin_lock.Package") as mock_package_class:
            mock_package_instance = mock.MagicMock()
            mock_package_class.return_value = mock_package_instance

            # Mock PortMap
            with mock.patch("chipflow_lib.pin_lock.PortMap") as mock_port_map_class:
                mock_port_map_instance = mock.MagicMock()
                mock_port_map_class.return_value = mock_port_map_instance

                # Run the function
                lock_pins()

                # Verify Package was initialized with our mock package type
                mock_package_class.assert_called_with(package_type=mock_package_type)

                # Check that add_pad was called for each pad
                calls = [
                    mock.call("clk", {"type": "clock", "loc": "1"}),
                    mock.call("rst", {"type": "reset", "loc": "2"}),
                    mock.call("vdd", {"type": "power", "loc": "3"}),
                    mock.call("gnd", {"type": "ground", "loc": "4"})
                ]
                mock_package_instance.add_pad.assert_has_calls(calls, any_order=True)

                # Verify port allocation happened
                self.assertTrue(mock_package_type.allocate.called)

                # Verify LockFile creation
                mock_lock_file.assert_called_once()

                # Check that open was called for writing
                #mock_open.assert_called_once_with('pins.lock', 'w')

                # Verify write was called with the JSON data
                file_handle = mock_open.return_value.__enter__.return_value
                file_handle.write.assert_called_once_with('{"test": "json"}')

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("chipflow_lib.pin_lock._parse_config")
    @mock.patch("chipflow_lib.pin_lock.top_interfaces")
    @mock.patch("pathlib.Path.exists")
    @mock.patch("pathlib.Path.read_text")
    @mock.patch("chipflow_lib.pin_lock.LockFile.model_validate_json")
    @mock.patch("chipflow_lib.pin_lock.PACKAGE_DEFINITIONS", new_callable=dict)
    @mock.patch("chipflow_lib.pin_lock.LockFile")
    def test_lock_pins_with_existing_lockfile(self, mock_lock_file, mock_package_defs,
                                             mock_validate_json, mock_read_text,
                                             mock_exists, mock_top_interfaces,
                                             mock_parse_config, mock_open):
        """Test lock_pins function with an existing pins.lock file"""
        # Setup mock package definitions
        mock_package_type = MockPackageType(name="cf20")
        mock_package_defs["cf20"] = mock_package_type

        # Setup mocks
        mock_exists.return_value = True  # Existing pins.lock
        mock_read_text.return_value = '{"mock": "json"}'

        # Mock LockFile instance for validate_json
        mock_old_lock = mock.MagicMock()
        mock_old_lock.package.check_pad.return_value = None  # No conflicting pads
        mock_old_lock.port_map.get_ports.return_value = None  # No existing ports
        mock_validate_json.return_value = mock_old_lock

        # Set up LockFile mock for constructor
        mock_new_lock = mock.MagicMock()
        mock_lock_file.return_value = mock_new_lock
        # Make model_dump_json return a valid JSON string
        mock_new_lock.model_dump_json.return_value = '{"test": "json"}'

        # Mock config
        mock_config = {
            "chipflow": {
                "project_name": "test",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "silicon": {
                    "process": "ihp_sg13g2",
                    "package": "cf20",
                    "pads": {
                        "clk": {"type": "clock", "loc": "1"},
                        "rst": {"type": "reset", "loc": "2"}
                    },
                    "power": {
                        "vdd": {"type": "power", "loc": "3"},
                        "gnd": {"type": "ground", "loc": "4"}
                    }
                }
            }
        }
        mock_parse_config.return_value = mock_config

        # Mock top_interfaces
        mock_interface = {
            "comp1": {
                "interface": {
                    "members": {
                        "uart": {
                            "type": "interface",
                            "members": {
                                "tx": {"type": "port", "width": 1, "dir": "o"},
                                "rx": {"type": "port", "width": 1, "dir": "i"}
                            }
                        }
                    }
                }
            }
        }
        mock_top_interfaces.return_value = (None, mock_interface)

        # Import and run lock_pins
        from chipflow_lib.pin_lock import lock_pins

        # Mock the Package.__init__ to avoid validation errors
        with mock.patch("chipflow_lib.pin_lock.Package") as mock_package_class:
            mock_package_instance = mock.MagicMock()
            mock_package_class.return_value = mock_package_instance

            # Mock PortMap
            with mock.patch("chipflow_lib.pin_lock.PortMap") as mock_port_map_class:
                mock_port_map_instance = mock.MagicMock()
                mock_port_map_class.return_value = mock_port_map_instance

                # Run the function
                lock_pins()

                # Verify read_text was called to read the existing lockfile
                mock_read_text.assert_called_once()

                # Verify model_validate_json was called to parse the lockfile
                mock_validate_json.assert_called_once_with('{"mock": "json"}')

                # Verify Package was initialized with our mock package type
                mock_package_class.assert_called_with(package_type=mock_package_type)

                # Check that add_pad was called for each pad
                calls = [
                    mock.call("clk", {"type": "clock", "loc": "1"}),
                    mock.call("rst", {"type": "reset", "loc": "2"}),
                    mock.call("vdd", {"type": "power", "loc": "3"}),
                    mock.call("gnd", {"type": "ground", "loc": "4"})
                ]
                mock_package_instance.add_pad.assert_has_calls(calls, any_order=True)

                # Verify LockFile creation
                mock_lock_file.assert_called_once()

                # Check that open was called for writing the new lockfile
                #mock_open.assert_called_once_with('pins.lock', 'w')

                # Verify data was written
                file_handle = mock_open.return_value.__enter__.return_value
                file_handle.write.assert_called_once_with('{"test": "json"}')

    @mock.patch("chipflow_lib.pin_lock._parse_config")
    @mock.patch("pathlib.Path.exists")
    @mock.patch("pathlib.Path.read_text")
    @mock.patch("chipflow_lib.pin_lock.LockFile.model_validate_json")
    @mock.patch("chipflow_lib.pin_lock.PACKAGE_DEFINITIONS", new_callable=dict)
    @mock.patch("chipflow_lib.pin_lock.LockFile")
    def test_lock_pins_with_conflicts(self, mock_lock_file, mock_package_defs,
                                     mock_validate_json, mock_read_text,
                                     mock_exists, mock_parse_config):
        """Test lock_pins function with conflicting pins in lockfile vs config"""
        # Setup mock package definitions
        mock_package_type = MockPackageType(name="cf20")
        mock_package_defs["cf20"] = mock_package_type

        # Setup mocks
        mock_exists.return_value = True  # Existing pins.lock
        mock_read_text.return_value = '{"mock": "json"}'

        # Mock LockFile instance with conflicting pad
        mock_old_lock = mock.MagicMock()

        # Create a conflicting port
        class MockConflictPort:
            def __init__(self):
                self.pins = ["5"]  # Different from config

        mock_old_lock.package.check_pad.return_value = MockConflictPort()
        mock_validate_json.return_value = mock_old_lock

        # Set up new LockFile mock for constructor (will not be reached in this test)
        mock_new_lock = mock.MagicMock()
        mock_lock_file.return_value = mock_new_lock

        # Mock config
        mock_config = {
            "chipflow": {
                "project_name": "test",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "silicon": {
                    "process": "ihp_sg13g2",
                    "package": "cf20",
                    "pads": {
                        "clk": {"type": "clock", "loc": "1"},  # This will be checked by check_pad
                    },
                    "power": {}
                }
            }
        }
        mock_parse_config.return_value = mock_config

        # Import lock_pins
        from chipflow_lib.pin_lock import lock_pins

        # Mock the Package.__init__
        with mock.patch("chipflow_lib.pin_lock.Package") as mock_package_class:
            mock_package_instance = mock.MagicMock()
            mock_package_class.return_value = mock_package_instance

            # Test for exception
            with self.assertRaises(ChipFlowError) as cm:
                lock_pins()

            # Verify error message
            self.assertIn("chipflow.toml conflicts with pins.lock", str(cm.exception))

            # Verify the exception is raised before we reach the LockFile constructor
            mock_lock_file.assert_not_called()

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("chipflow_lib.pin_lock._parse_config")
    @mock.patch("chipflow_lib.pin_lock.top_interfaces")
    @mock.patch("pathlib.Path.exists")
    @mock.patch("pathlib.Path.read_text")
    @mock.patch("chipflow_lib.pin_lock.LockFile.model_validate_json")
    @mock.patch("chipflow_lib.pin_lock.PACKAGE_DEFINITIONS", new_callable=dict)
    @mock.patch("chipflow_lib.pin_lock.LockFile")
    def test_lock_pins_reuse_existing_ports(self, mock_lock_file, mock_package_defs,
                                           mock_validate_json, mock_read_text,
                                           mock_exists, mock_top_interfaces,
                                           mock_parse_config, mock_open):
        """Test lock_pins function reusing existing port allocations"""
        # Setup mock package definitions
        mock_package_type = MockPackageType(name="cf20")
        mock_package_defs["cf20"] = mock_package_type

        # Setup mocks
        mock_exists.return_value = True  # Existing pins.lock
        mock_read_text.return_value = '{"mock": "json"}'

        # Mock LockFile instance for existing lock
        mock_old_lock = mock.MagicMock()
        mock_old_lock.package.check_pad.return_value = None  # No conflicting pads

        # Create existing ports to be reused
        existing_ports = {
            "tx": mock.MagicMock(pins=["10"]),
            "rx": mock.MagicMock(pins=["11"])
        }
        mock_old_lock.port_map.get_ports.return_value = existing_ports
        mock_validate_json.return_value = mock_old_lock

        # Set up new LockFile mock for constructor
        mock_new_lock = mock.MagicMock()
        mock_lock_file.return_value = mock_new_lock
        # Make model_dump_json return a valid JSON string
        mock_new_lock.model_dump_json.return_value = '{"test": "json"}'

        # Mock config
        mock_config = {
            "chipflow": {
                "project_name": "test",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "silicon": {
                    "process": "ihp_sg13g2",
                    "package": "cf20",
                    "pads": {},
                    "power": {}
                }
            }
        }
        mock_parse_config.return_value = mock_config

        # Mock top_interfaces
        mock_interface = {
            "comp1": {
                "interface": {
                    "members": {
                        "uart": {
                            "type": "interface",
                            "members": {
                                "tx": {"type": "port", "width": 1, "dir": "o"},
                                "rx": {"type": "port", "width": 1, "dir": "i"}
                            }
                        }
                    }
                }
            }
        }
        mock_top_interfaces.return_value = (None, mock_interface)

        # Import and run lock_pins
        from chipflow_lib.pin_lock import lock_pins

        # Mock the Package.__init__ to avoid validation errors
        with mock.patch("chipflow_lib.pin_lock.Package") as mock_package_class:
            mock_package_instance = mock.MagicMock()
            mock_package_class.return_value = mock_package_instance

            # Mock PortMap
            with mock.patch("chipflow_lib.pin_lock.PortMap") as mock_port_map_class:
                mock_port_map_instance = mock.MagicMock()
                mock_port_map_class.return_value = mock_port_map_instance

                # Run the function
                lock_pins()

                # Verify get_ports was called to retrieve existing ports
                mock_old_lock.port_map.get_ports.assert_called_with("comp1", "uart")

                # Verify existing ports were reused by calling add_ports
                mock_port_map_instance.add_ports.assert_called_with("comp1", "uart", existing_ports)

                # Verify LockFile creation with reused ports
                mock_lock_file.assert_called_once()

                # Check that open was called for writing
                #mock_open.assert_called_once_with('pins.lock', 'w')

                # Verify data was written
                file_handle = mock_open.return_value.__enter__.return_value
                file_handle.write.assert_called_once_with('{"test": "json"}')
