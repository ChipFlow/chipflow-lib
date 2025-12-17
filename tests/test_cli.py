# SPDX-License-Identifier: BSD-2-Clause

import pytest
import unittest

from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

from chipflow import ChipFlowError
from chipflow.cli import run
from chipflow.config import Config, ChipFlowConfig

class MockCommand:
    """Mock command for testing CLI"""

    def build_cli_parser(self, parser):
        parser.add_argument("--option", help="Test option")
        parser.add_argument("action", choices=["valid", "error", "unexpected"])

    def run_cli(self, args):
        if args.action == "error":
            raise ChipFlowError("Command error")
        elif args.action == "unexpected":
            raise ValueError("Unexpected error")
        # Valid action does nothing

MOCK_CONFIG = Config(chipflow=ChipFlowConfig(project_name="test",
                                             steps={"test": "test:MockStep"}
                                             ))

class TestCLI(unittest.TestCase):
    @mock.patch("chipflow.cli._parse_config")
    @mock.patch("chipflow.cli.PinCommand")
    @mock.patch("chipflow.cli._get_cls_by_reference")
    def test_run_success(self, mock_get_cls, mock_pin_command, mock_parse_config):
        """Test CLI run with successful command execution"""
        # Setup mocks
        mock_parse_config.return_value = MOCK_CONFIG

        mock_pin_cmd = MockCommand()
        mock_pin_command.return_value = mock_pin_cmd

        mock_test_cmd = MockCommand()
        mock_get_cls.return_value = lambda config: mock_test_cmd

        # Capture stdout for assertion
        with mock.patch("sys.stdout") as mock_stdout:
            # Run with valid action
            run(["test", "valid"])

            # No error message should be printed
            mock_stdout.write.assert_not_called()

    @mock.patch("chipflow.cli._parse_config")
    @mock.patch("chipflow.cli.PinCommand")
    @mock.patch("chipflow.cli._get_cls_by_reference")
    def test_run_command_error(self, mock_get_cls, mock_pin_command, mock_parse_config):
        """Test CLI run with command raising ChipFlowError"""
        # Setup mocks
        mock_parse_config.return_value = MOCK_CONFIG

        mock_pin_cmd = MockCommand()
        mock_pin_command.return_value = mock_pin_cmd

        mock_test_cmd = MockCommand()
        mock_get_cls.return_value = lambda config: mock_test_cmd

        # Capture stdout for assertion
        with redirect_stdout(StringIO()) as buffer:
            with pytest.raises(SystemExit) as systemexit:
                # Run with error action
                run(["test", "error"])

                assert systemexit.type is SystemExit
                assert systemexit.value.code == 1

        self.assertIn("Error while executing `test error`", buffer.getvalue())

    @mock.patch("chipflow.cli._parse_config")
    @mock.patch("chipflow.cli.PinCommand")
    @mock.patch("chipflow.cli._get_cls_by_reference")
    def test_run_unexpected_error(self, mock_get_cls, mock_pin_command, mock_parse_config):
        """Test CLI run with command raising unexpected exception"""
        # Setup mocks
        mock_parse_config.return_value = MOCK_CONFIG

        mock_pin_cmd = MockCommand()
        mock_pin_command.return_value = mock_pin_cmd

        mock_test_cmd = MockCommand()
        mock_get_cls.return_value = lambda config: mock_test_cmd

        # Capture stdout for assertion
        with redirect_stdout(StringIO()) as buffer:
            with pytest.raises(SystemExit) as systemexit:
                # Run with unexpected error action
                run(["test", "unexpected"])

                assert systemexit.type is SystemExit
                assert systemexit.value.code == 1

            # Error message should be printed
            self.assertIn("Error while executing `test unexpected`", buffer.getvalue())
            self.assertIn("Unexpected error", buffer.getvalue())

    @mock.patch("chipflow.cli._parse_config")
    @mock.patch("chipflow.cli.PinCommand")
    def test_step_init_error(self, mock_pin_command, mock_parse_config):
        """Test CLI run with error initializing step"""
        # Setup mocks
        mock_parse_config.return_value = MOCK_CONFIG

        mock_pin_cmd = MockCommand()
        mock_pin_command.return_value = mock_pin_cmd

        # Make _get_cls_by_reference raise an exception during step initialization
        with mock.patch("chipflow.cli._get_cls_by_reference") as mock_get_cls:
            mock_get_cls.return_value = mock.Mock(side_effect=Exception("Init error"))

            with self.assertRaises(ChipFlowError) as cm:
                run(["test", "valid"])

            self.assertIn("Encountered error while initializing step", str(cm.exception))

    @mock.patch("chipflow.cli._parse_config")
    @mock.patch("chipflow.cli.PinCommand")
    @mock.patch("chipflow.cli._get_cls_by_reference")
    def test_build_parser_error(self, mock_get_cls, mock_pin_command, mock_parse_config):
        """Test CLI run with error building CLI parser"""
        # Setup mocks
        mock_parse_config.return_value = MOCK_CONFIG

        # Make pin command raise an error during build_cli_parser
        mock_pin_cmd = mock.Mock()
        mock_pin_cmd.build_cli_parser.side_effect = Exception("Parser error")
        mock_pin_command.return_value = mock_pin_cmd

        mock_test_cmd = mock.Mock()
        mock_test_cmd.build_cli_parser.side_effect = Exception("Parser error")
        mock_get_cls.return_value = lambda config: mock_test_cmd

        with self.assertRaises(ChipFlowError) as cm:
            run(["pin", "lock"])

        self.assertIn("Encountered error while building CLI argument parser", str(cm.exception))

#     @mock.patch("chipflow.cli._parse_config")
#     @mock.patch("chipflow.cli.PinCommand")
#     @mock.patch("chipflow.cli._get_cls_by_reference")
#     def test_verbosity_flags(self, mock_get_cls, mock_pin_command, mock_parse_config):
#         """Test CLI verbosity flags"""
#         # Setup mocks
#         mock_parse_config.return_value = MOCK_CONFIG
#
#         mock_pin_cmd = MockCommand()
#         mock_pin_command.return_value = mock_pin_cmd
#
#         mock_test_cmd = MockCommand()
#         mock_get_cls.return_value = lambda config: mock_test_cmd
#
#         # Save original log level
#         original_level = logging.getLogger().level
#
#         try:
#             # Test with -v
#             with mock.patch("sys.stdout"):
#                 run(["-v", "test", "valid"])
#                 self.assertEqual(logging.getLogger().level, logging.INFO)
#
#             # Reset log level
#             logging.getLogger().setLevel(original_level)
#
#             # Test with -v -v
#             with mock.patch("sys.stdout"):
#                 run(["-v", "-v", "test", "valid"])
#                 self.assertEqual(logging.getLogger().level, logging.DEBUG)
#         finally:
#             # Restore original log level
#             logging.getLogger().setLevel(original_level)
