# SPDX-License-Identifier: BSD-2-Clause
import unittest
from unittest import mock
import tempfile
import os
import json
from pathlib import Path

from chipflow_lib.pin_lock import (
    lock_pins,
    PinCommand
)
from chipflow_lib.config_models import Config


class TestPinLockAdvanced(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)

        # Mock environment variables
        self.env_patcher = mock.patch.dict(os.environ, {"CHIPFLOW_ROOT": self.temp_dir.name})
        self.env_patcher.start()

        # Create test data - valid for Pydantic Config model
        self.mock_config = {
            "chipflow": {
                "project_name": "test_project",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "silicon": {
                    "process": "ihp_sg13g2",
                    "package": "pga144",
                    "pads": {
                        "pad1": {"type": "io", "loc": "1"},
                        "pad2": {"type": "clock", "loc": "2"}
                    },
                    "power": {
                        "vdd": {"type": "power", "loc": "3"},
                        "vss": {"type": "ground", "loc": "4"}
                    }
                },
                "clocks": {
                    "default": "sys_clk"
                },
                "resets": {
                    "default": "sys_rst_n"
                },
                "top": {
                    "component1": "module:Component"
                }
            }
        }

    def tearDown(self):
        self.env_patcher.stop()
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    @mock.patch('chipflow_lib.pin_lock._parse_config')
    @mock.patch('chipflow_lib.pin_lock.top_interfaces')
    @mock.patch('chipflow_lib.pin_lock.PACKAGE_DEFINITIONS')
    @mock.patch('chipflow_lib.pin_lock.Config.model_validate')
    def test_pydantic_lockfile_creation(self, mock_model_validate, mock_package_defs, mock_top_interfaces, mock_parse_config):
        """Test lock_pins creates a proper LockFile using Pydantic models"""
        # Import the Pydantic models we need
        from chipflow_lib.platforms.utils import _QuadPackageDef
        from chipflow_lib.config_models import SiliconConfig, ChipFlowConfig, PadConfig

        # Create a proper PackageDef instance (real Pydantic object, not a mock)
        package_def = _QuadPackageDef(name="test_package", width=10, height=10)

        # Since we can't modify allocate directly on a Pydantic model instance,
        # create a patch for the allocate method at module level
        with mock.patch.object(_QuadPackageDef, 'allocate', autospec=True) as mock_allocate:
            # Configure the mock to return predictable values
            mock_allocate.return_value = ["10", "11"]

            # Set up package definitions with our real Pydantic object
            mock_package_defs.__getitem__.return_value = package_def
            mock_package_defs.__contains__.return_value = True

            # Create real Pydantic objects for configuration instead of mocks
            # Start with pads and power
            pads = {}
            for name, config in self.mock_config["chipflow"]["silicon"]["pads"].items():
                pads[name] = PadConfig(
                    type=config["type"],
                    loc=config["loc"]
                )

            power = {}
            for name, config in self.mock_config["chipflow"]["silicon"]["power"].items():
                power[name] = PadConfig(
                    type=config["type"],
                    loc=config["loc"]
                )

            # Create a Silicon config object
            silicon_config = SiliconConfig(
                process="ihp_sg13g2",
                package="pga144",
                pads=pads,
                power=power
            )

            # Create the Chipflow config object with proper StepsConfig
            from chipflow_lib.config_models import StepsConfig

            steps_config = StepsConfig(
                silicon="chipflow_lib.steps.silicon:SiliconStep"
            )

            chipflow_config = ChipFlowConfig(
                project_name="test_project",
                silicon=silicon_config,
                steps=steps_config
            )

            # Create the full Config object
            config_model = Config(chipflow=chipflow_config)

            # Set up the mock model_validate to return our real Pydantic config object
            mock_model_validate.return_value = config_model

            # Set up parse_config to return the dict version
            mock_parse_config.return_value = self.mock_config

            # Mock top interfaces to return something simple
            mock_interface = {
                "component1": {
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
            mock_top_interfaces.return_value = ({}, mock_interface)

            # Call lock_pins with mocked file operations
            with mock.patch('builtins.print'), \
                 mock.patch('pathlib.Path.exists', return_value=False), \
                 mock.patch('chipflow_lib.pin_lock.LockFile.model_validate_json'):
                lock_pins()

            # Check that a lockfile was created
            lockfile_path = Path('pins.lock')
            self.assertTrue(lockfile_path.exists())

            # Read the lockfile
            with open(lockfile_path, 'r') as f:
                lock_data = json.load(f)

            # Verify it has the expected structure (Pydantic model)
            self.assertIn("process", lock_data)
            self.assertIn("package", lock_data)
            self.assertIn("port_map", lock_data)
            self.assertIn("metadata", lock_data)

            # Verify process is correct
            self.assertEqual(lock_data["process"], "ihp_sg13g2")

            # Verify package
            self.assertIn("package_type", lock_data["package"])

            # Verify port_map has the right structure for our uart interface
            self.assertIn("component1", lock_data["port_map"])
            self.assertIn("uart", lock_data["port_map"]["component1"])
            self.assertIn("power", lock_data["package"])

            # Verify port_map has our component
            self.assertIn("component1", lock_data["port_map"])



class TestPinCommandCLI(unittest.TestCase):
    def test_build_cli_parser(self):
        """Test build_cli_parser method"""
        # Create mock parser
        parser = mock.Mock()
        subparsers = mock.Mock()
        parser.add_subparsers.return_value = subparsers

        # Create PinCommand
        cmd = PinCommand({"test": "config"})

        # Call build_cli_parser
        cmd.build_cli_parser(parser)

        # Check that add_subparsers was called
        parser.add_subparsers.assert_called_once()
        # Check that add_parser was called with "lock"
        subparsers.add_parser.assert_called_once_with("lock", help=mock.ANY)

    def test_run_cli_lock(self):
        """Test run_cli method with lock action"""
        # Create mock args
        args = mock.Mock()
        args.action = "lock"

        # Create PinCommand
        cmd = PinCommand({"test": "config"})

        # Patch lock method
        with mock.patch.object(cmd, "lock") as mock_lock:
            # Call run_cli
            cmd.run_cli(args)

            # Check that lock was called
            mock_lock.assert_called_once()