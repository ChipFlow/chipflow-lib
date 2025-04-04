# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest
import tempfile
from unittest import mock

from chipflow_lib.platforms.utils import (
    Package, PortMap, LockFile, Process, _QuadPackageDef
)
from chipflow_lib.config_models import Config, SiliconConfig, PadConfig, StepsConfig, ChipFlowConfig
from chipflow_lib.pin_lock import (
    count_member_pins, allocate_pins, lock_pins, PinCommand
)


# Define a MockPackageType for testing
class MockPackageType:
    """Mock for package type class used in tests"""
    def __init__(self, name="test_package"):
        self.name = name
        self.type = "_PGAPackageDef"  # This is needed for Pydantic discrimination
        self.pins = set([str(i) for i in range(1, 100)])  # Create pins 1-99
        self.width = 50  # For Pydantic compatibility
        self.height = 50  # For Pydantic compatibility

    def sortpins(self, pins):
        return sorted(list(pins), key=int)

    def allocate(self, available, width):
        # Simple allocation - just return the first 'width' pins from available
        available_list = sorted(list(available), key=int)
        allocated = available_list[:width]
        return allocated


class TestPinLock(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        # Mock environment for testing
        self.chipflow_root_patcher = mock.patch.dict(os.environ, {"CHIPFLOW_ROOT": self.temp_dir.name})
        self.chipflow_root_patcher.start()
        # Create test configuration
        # Create a proper Pydantic model
        self.silicon_config = SiliconConfig(
            process=Process.IHP_SG13G2,
            package="cf20",
            pads={
                "clk": PadConfig(type="clock", loc="1"),
                "rst": PadConfig(type="reset", loc="2"),
                "led": PadConfig(type="o", loc="3")
            },
            power={
                "vdd": PadConfig(type="power", loc="4"),
                "vss": PadConfig(type="ground", loc="5")
            }
        )
        # Create the steps config
        self.steps_config = StepsConfig(
            silicon="chipflow_lib.steps.silicon:SiliconStep"
        )
        # Create a full chipflow config
        self.chipflow_config = ChipFlowConfig(
            project_name="test_project",
            top={"soc": "module:SoC"},
            steps=self.steps_config,
            silicon=self.silicon_config,
            clocks={"default": "clk"},
            resets={"default": "rst"}
        )
        # Create the complete config
        self.config = Config(chipflow=self.chipflow_config)
        # Also create a dict version for compatibility with some functions
        self.config_dict = {
            "chipflow": {
                "project_name": "test_project",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "silicon": {
                    "process": "ihp_sg13g2",
                    "package": "cf20",
                    "pads": {
                        "clk": {"type": "clock", "loc": "1"},
                        "rst": {"type": "reset", "loc": "2"},
                        "led": {"type": "o", "loc": "3"}
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


    @mock.patch("chipflow_lib.pin_lock._parse_config")
    @mock.patch("chipflow_lib.pin_lock.Config.model_validate")
    @mock.patch("chipflow_lib.pin_lock.PACKAGE_DEFINITIONS", new={"cf20": _QuadPackageDef(name="cf20", width=50, height=50)})
    @mock.patch("chipflow_lib.pin_lock.top_interfaces")
    @mock.patch("pathlib.Path.exists")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    def test_lock_pins_new_file(self, mock_open, mock_exists, mock_top_interfaces,
                              mock_config_validate, mock_parse_config):
        """Test lock_pins function with a new pins.lock file"""
        # Set up mocks
        mock_parse_config.return_value = self.config_dict
        mock_config_validate.return_value = self.config
        mock_exists.return_value = False  # No existing file
        mock_top_interfaces.return_value = ({}, self.mock_interfaces)
        # Call the function with real objects
        with mock.patch("chipflow_lib.pin_lock.logger"):
            lock_pins()
        # Verify open was called for writing the pin lock file
        mock_open.assert_called_once_with('pins.lock', 'w')
        # Check that the file was written (write was called)
        mock_open().write.assert_called_once()
        # We can't easily verify the exact content that was written without
        # fully mocking all the complex Pydantic objects, but we can check that
        # a write happened, which confirms basic functionality

    @mock.patch("chipflow_lib.pin_lock._parse_config")
    @mock.patch("chipflow_lib.pin_lock.Config.model_validate")
    @mock.patch("chipflow_lib.pin_lock.PACKAGE_DEFINITIONS", new={"cf20": _QuadPackageDef(name="cf20", width=50, height=50)})
    @mock.patch("chipflow_lib.pin_lock.top_interfaces")
    @mock.patch("pathlib.Path.exists")
    @mock.patch("pathlib.Path.read_text")
    @mock.patch("chipflow_lib.pin_lock.LockFile.model_validate_json")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    def test_lock_pins_with_existing_lockfile(self, mock_open, mock_validate_json,
                                           mock_read_text, mock_exists, mock_top_interfaces,
                                           mock_config_validate, mock_parse_config):
        """Test lock_pins function with an existing pins.lock file"""
        # Setup mocks
        mock_parse_config.return_value = self.config_dict
        mock_config_validate.return_value = self.config
        mock_exists.return_value = True  # Existing file
        mock_read_text.return_value = '{"mock":"json"}'
        mock_top_interfaces.return_value = ({}, self.mock_interfaces)
        # Create a package for the existing lock file
        package_def = _QuadPackageDef(name="cf20", width=50, height=50)
        # Create a Package instance with the package_def
        package = Package(
            package_type=package_def,
            clocks={},
            resets={},
            power={}
        )
        # Create a PortMap instance
        port_map = PortMap({})
        # Create the LockFile instance
        old_lock = LockFile(
            process=Process.IHP_SG13G2,
            package=package,
            port_map=port_map,
            metadata={}
        )
        # Setup the mock to return our LockFile
        mock_validate_json.return_value = old_lock
        # Call the function
        with mock.patch("chipflow_lib.pin_lock.logger"):
            lock_pins()
        # Verify file operations
        mock_read_text.assert_called_once()
        mock_validate_json.assert_called_once_with('{"mock":"json"}')
        mock_open.assert_called_once_with('pins.lock', 'w')
        mock_open().write.assert_called_once()
        # Since we're using real objects, we'd need complex assertions to
        # verify the exact behavior. But the above confirms the basic flow
        # of reading the existing file and writing a new one.


class TestPinCommand(unittest.TestCase):
    @mock.patch("chipflow_lib.pin_lock.lock_pins")
    def test_pin_command(self, mock_lock_pins):
        """Test PinCommand functionality"""
        # Create config
        config = {"test": "config"}
        # Create command instance
        cmd = PinCommand(config)
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


if __name__ == "__main__":
    unittest.main()