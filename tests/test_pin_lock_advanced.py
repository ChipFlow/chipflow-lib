# SPDX-License-Identifier: BSD-2-Clause
import unittest
from unittest import mock
import tempfile
import os
import json
from pathlib import Path

from chipflow_lib.platforms.utils import LockFile, Package, Port
from chipflow_lib import ChipFlowError
from chipflow_lib.pin_lock import (
    lock_pins,
    count_member_pins,
    allocate_pins,
    PinCommand
)


class TestPinLockAdvanced(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)

        # Mock environment variables
        self.env_patcher = mock.patch.dict(os.environ, {"CHIPFLOW_ROOT": self.temp_dir.name})
        self.env_patcher.start()

        # Create test data
        self.mock_config = {
            "chipflow": {
                "silicon": {
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