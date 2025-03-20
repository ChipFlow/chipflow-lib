# amaranth: UnusedElaboratable=no

# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest
from unittest import mock
import argparse
import tempfile


from amaranth import Module

from chipflow_lib import ChipFlowError
from chipflow_lib.steps.silicon import SiliconStep, SiliconTop


class TestSiliconStep(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)

        # Mock environment for testing
        self.chipflow_root_patcher = mock.patch.dict(
            os.environ, {"CHIPFLOW_ROOT": self.temp_dir.name}
        )
        self.chipflow_root_patcher.start()

        # Create basic config for tests
        self.config = {
            "chipflow": {
                "project_name": "test_project",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "top": {
                    "mock_component": "module.MockComponent"
                },
                "silicon": {
                    "package": "cf20",
                    "process": "ihp_sg13g2",
                    "debug": {
                        "heartbeat": True
                    },
                    "pads": {},
                    "power": {}
                }
            }
        }

    def tearDown(self):
        self.chipflow_root_patcher.stop()
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    @mock.patch("chipflow_lib.steps.silicon.SiliconTop")
    def test_init(self, mock_silicontop_class):
        """Test SiliconStep initialization"""
        step = SiliconStep(self.config)

        # Check that attributes are correctly set
        self.assertEqual(step.config, self.config)
        self.assertEqual(step.project_name, "test_project")
        self.assertEqual(step.silicon_config, self.config["chipflow"]["silicon"])
        # Check that SiliconPlatform was initialized correctly
        self.assertIsNotNone(step.platform)

    @mock.patch("chipflow_lib.steps.silicon.SiliconTop")
    @mock.patch("chipflow_lib.steps.silicon.SiliconPlatform")
    @mock.patch("chipflow_lib.steps.silicon.top_interfaces")
    def test_prepare(self, mock_top_interfaces, mock_platform_class, mock_silicontop_class):
        """Test prepare method"""
        mock_platform = mock_platform_class.return_value
        mock_platform.build.return_value = "/path/to/rtlil"

        mock_silicontop = mock_silicontop_class.return_value

        # Mock top_interfaces to avoid UnusedElaboratable
        mock_top_interfaces.return_value = ({"mock_component": mock.MagicMock()}, {})

        # Create SiliconStep instance
        step = SiliconStep(self.config)

        # Call the method
        result = step.prepare()

        # Verify that platform.build was called correctly
        mock_platform.build.assert_called_once()
        # Verify the first arg is a SiliconTop instance
        args, kwargs = mock_platform.build.call_args
        self.assertEqual(args[0], mock_silicontop)
        # Verify the name parameter
        self.assertEqual(kwargs["name"], "test_project")
        self.assertEqual(mock_silicontop_class.call_args[0][0], self.config)

        # Check result
        self.assertEqual(result, "/path/to/rtlil")

    def test_build_cli_parser(self):
        """Test build_cli_parser method"""
        # Create a mock parser
        parser = mock.MagicMock()
        subparsers = mock.MagicMock()
        parser.add_subparsers.return_value = subparsers

        # Create SiliconStep instance
        step = SiliconStep(self.config)

        # Call the method
        step.build_cli_parser(parser)

        # Verify parser setup
        parser.add_subparsers.assert_called_once_with(dest="action")
        # Check that prepare and submit subparsers were added
        self.assertEqual(subparsers.add_parser.call_count, 2)
        # Check that dry-run argument was added to submit parser
        submit_parser = subparsers.add_parser.return_value
        submit_parser.add_argument.assert_called_with(
            "--dry-run", help=argparse.SUPPRESS,
            default=False, action="store_true"
        )

    @mock.patch("chipflow_lib.steps.silicon.SiliconPlatform")
    @mock.patch("chipflow_lib.steps.silicon.top_interfaces")
    @mock.patch("chipflow_lib.steps.silicon.dotenv.load_dotenv")
    @mock.patch("chipflow_lib.steps.silicon.SiliconStep.submit")
    @mock.patch("chipflow_lib.steps.silicon.SiliconStep.prepare")
    def test_cli_prepare(self, mock_prepare, mock_submit, mock_dotenv, mock_top_interfaces, mock_platform_class):
        """Test prepare method"""
        mock_platform = mock_platform_class.return_value
        mock_platform.build.return_value = "/path/to/rtlil"

        # Create mock args
        args = mock.MagicMock()
        args.action = "prepare"

        # Create SiliconStep instance
        step = SiliconStep(self.config)

        # Set up the mock to handle SiliconTop

        # Call the method
        step.run_cli(args)

        mock_prepare.assert_called_once()
        mock_submit.assert_not_called()
        # Verify dotenv not loaded for prepare
        mock_dotenv.assert_not_called()

    @mock.patch("chipflow_lib.steps.silicon.SiliconTop")
    @mock.patch("chipflow_lib.steps.silicon.SiliconStep.prepare")
    @mock.patch("chipflow_lib.steps.silicon.SiliconStep.submit")
    @mock.patch("chipflow_lib.steps.silicon.dotenv.load_dotenv")
    def test_run_cli_submit(self, mock_load_dotenv, mock_submit, mock_prepare, mock_silicontop_class):
        """Test run_cli with submit action"""
        # Setup mocks
        mock_prepare.return_value = "/path/to/rtlil"

        # Add environment variables
        with mock.patch.dict(os.environ, {
            "CHIPFLOW_API_KEY_ID": "api_key_id",
            "CHIPFLOW_API_KEY_SECRET": "api_key_secret"
        }):
            # Create mock args
            args = mock.MagicMock()
            args.action = "submit"
            args.dry_run = False

            # Create SiliconStep instance
            step = SiliconStep(self.config)

            # Call the method
            step.run_cli(args)

            # Verify prepare and submit were called
            mock_prepare.assert_called_once()
            mock_submit.assert_called_once_with("/path/to/rtlil", dry_run=False)
            # Verify dotenv was loaded for submit
            mock_load_dotenv.assert_called_once()

    @mock.patch("chipflow_lib.steps.silicon.SiliconTop")
    @mock.patch("chipflow_lib.steps.silicon.SiliconPlatform")
    @mock.patch("chipflow_lib.steps.silicon.SiliconStep.submit")
    @mock.patch("chipflow_lib.steps.silicon.dotenv.load_dotenv")
    @mock.patch("chipflow_lib.steps.silicon.top_interfaces")
    def test_run_cli_submit_dry_run(self, mock_top_interfaces, mock_load_dotenv, mock_submit, mock_platform_class, mock_silicontop_class):
        """Test run_cli with submit action in dry run mode"""
        # Setup mocks
        mock_platform = mock_platform_class.return_value
        mock_platform.build.return_value = "/path/to/rtlil"
        mock_top_interfaces.return_value = ({"mock_component": mock.MagicMock()}, {})
        mock_platform.pinlock.port_map = {}

        # Create mock args
        args = mock.MagicMock()
        args.action = "submit"
        args.dry_run = True

        # Create SiliconStep instance
        step = SiliconStep(self.config)

        # Call the method
        step.run_cli(args)

        # Verify prepare and submit were called
        mock_platform.build.assert_called_once()
        mock_submit.assert_called_once_with("/path/to/rtlil", dry_run=True)
        # Verify dotenv was not loaded for dry run
        mock_load_dotenv.assert_not_called()
        mock_silicontop_class.assert_called_once_with(self.config)

    @mock.patch("chipflow_lib.steps.silicon.SiliconStep.prepare")
    @mock.patch("chipflow_lib.steps.silicon.dotenv.load_dotenv")
    def test_run_cli_submit_missing_project_name(self, mock_load_dotenv, mock_prepare):
        """Test run_cli with submit action but missing project name"""
        # Setup config without project_name
        config_no_project = {
            "chipflow": {
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "silicon": {
                    "package": "cf20",
                    "process": "ihp_sg13g2"
                }
            }
        }

        # Add environment variables
        with mock.patch.dict(os.environ, {
            "CHIPFLOW_API_KEY_ID": "api_key_id",
            "CHIPFLOW_API_KEY_SECRET": "api_key_secret"
        }):
            # Create mock args
            args = mock.MagicMock()
            args.action = "submit"
            args.dry_run = False

            # Create SiliconStep instance
            step = SiliconStep(config_no_project)

            # Test for exception
            with self.assertRaises(ChipFlowError) as cm:
                step.run_cli(args)

            # Verify error message mentions project_id
            self.assertIn("project_id", str(cm.exception))
            # Verify dotenv was loaded
            mock_load_dotenv.assert_called_once()

    @mock.patch("chipflow_lib.steps.silicon.SiliconStep.prepare")
    @mock.patch("chipflow_lib.steps.silicon.dotenv.load_dotenv")
    def test_run_cli_submit_missing_api_keys(self, mock_load_dotenv, mock_prepare):
        """Test run_cli with submit action but missing API keys"""
        # Create mock args
        args = mock.MagicMock()
        args.action = "submit"
        args.dry_run = False

        # Create SiliconStep instance
        step = SiliconStep(self.config)

        # Test for exception
        with self.assertRaises(ChipFlowError) as cm:
            step.run_cli(args)

        # Verify error message
        self.assertIn("CHIPFLOW_API_KEY_ID", str(cm.exception))
        self.assertIn("CHIPFLOW_API_KEY_SECRET", str(cm.exception))
        # Verify dotenv was loaded
        mock_load_dotenv.assert_called_once()

    @mock.patch("chipflow_lib.steps.silicon.subprocess.check_output")
    @mock.patch("chipflow_lib.steps.silicon.importlib.metadata.version")
    def test_submit_dry_run(self, mock_version, mock_check_output):
        """Test submit method with dry run option"""
        # Setup mocks for git commands - return strings, not bytes
        mock_check_output.side_effect = [
            "abcdef\n",  # git rev-parse
            ""           # git status (not dirty)
        ]

        # Setup version mocks
        mock_version.return_value = "1.0.0"

        # Setup platform mock
        platform_mock = mock.MagicMock()
        platform_mock._ports = {
            "port1": mock.MagicMock(
                pins=["1"],
                direction=mock.MagicMock(value="i")
            ),
            "port2": mock.MagicMock(
                pins=["2", "3"],
                direction=mock.MagicMock(value="o")
            )
        }

        # Create SiliconStep with mocked platform
        step = SiliconStep(self.config)
        step.platform = platform_mock

        # Mock print and capture output
        with mock.patch("builtins.print") as mock_print:
            # Call submit with dry run
            step.submit("/path/to/rtlil", dry_run=True)

            # Verify print was called twice
            self.assertEqual(mock_print.call_count, 2)
            # Verify JSON data was printed
            args = mock_print.call_args_list
            self.assertIn("data=", args[0][0][0])
            self.assertIn("files['config']=", args[1][0][0])

            # Verify no requests were made
            self.assertFalse(hasattr(step, "_request_made"))

    @mock.patch("chipflow_lib.steps.silicon.subprocess.check_output")
    @mock.patch("chipflow_lib.steps.silicon.importlib.metadata.version")
    @mock.patch("json.dumps")
    def test_config_json_content(self, mock_json_dumps, mock_version, mock_check_output):
        """Test the content of the config.json generated by submit"""
        # Setup mocks for git commands - need enough values for two calls to submit
        mock_check_output.side_effect = [
            "abcdef\n",  # git rev-parse for first submit
            "",          # git status for first submit
            "abcdef\n",  # git rev-parse for second submit
            ""           # git status for second submit
        ]

        # Setup version mocks
        mock_version.return_value = "1.0.0"

        # Create a custom platform mock with specific ports
        platform_mock = mock.MagicMock()
        platform_mock._ports = {
            "uart_tx": mock.MagicMock(
                pins=["A1"],
                direction=mock.MagicMock(value="o")
            ),
            "uart_rx": mock.MagicMock(
                pins=["B1"],
                direction=mock.MagicMock(value="i")
            ),
            "gpio": mock.MagicMock(
                pins=["C1", "C2", "C3"],
                direction=mock.MagicMock(value="io")
            )
        }

        # Create SiliconStep with mocked platform
        step = SiliconStep(self.config)
        step.platform = platform_mock

        # Mock the json.dumps to capture the config content
        def capture_json_args(*args, **kwargs):
            if len(args) > 0 and isinstance(args[0], dict) and "silicon" in args[0]:
                # Store the captured config for later assertion
                capture_json_args.captured_config = args[0]
            return "mocked_json_string"

        capture_json_args.captured_config = None
        mock_json_dumps.side_effect = capture_json_args

        # Call submit with dry run to avoid actual HTTP requests
        with mock.patch("builtins.print"):
            step.submit("/path/to/rtlil", dry_run=True)

        # Verify the config content
        config = capture_json_args.captured_config
        self.assertIsNotNone(config, "Config should have been captured")

        # Check dependency versions
        self.assertIn("dependency_versions", config)
        dep_versions = config["dependency_versions"]
        self.assertEqual(dep_versions["chipflow-lib"], "1.0.0")
        self.assertEqual(dep_versions["amaranth"], "1.0.0")

        # Check silicon section
        self.assertIn("silicon", config)
        silicon = config["silicon"]

        # Check process and package
        self.assertEqual(silicon["process"], "ihp_sg13g2")
        self.assertEqual(silicon["pad_ring"], "cf20")

        # Check pads configuration
        self.assertIn("pads", silicon)
        pads = silicon["pads"]

        # Check specific pads
        self.assertIn("uart_tx", pads)
        self.assertEqual(pads["uart_tx"]["loc"], "A1")
        self.assertEqual(pads["uart_tx"]["type"], "o")

        self.assertIn("uart_rx", pads)
        self.assertEqual(pads["uart_rx"]["loc"], "B1")
        self.assertEqual(pads["uart_rx"]["type"], "i")

        # Check multi-bit ports are correctly expanded
        self.assertIn("gpio0", pads)
        self.assertEqual(pads["gpio0"]["loc"], "C1")
        self.assertEqual(pads["gpio0"]["type"], "io")

        self.assertIn("gpio1", pads)
        self.assertEqual(pads["gpio1"]["loc"], "C2")

        self.assertIn("gpio2", pads)
        self.assertEqual(pads["gpio2"]["loc"], "C3")

        # Check power section exists and matches config
        self.assertIn("power", silicon)

        # Add a power entry to the config to test power section in the generated config
        self.config["chipflow"]["silicon"]["power"] = {
            "vdd": {"type": "power", "loc": "N1"},
            "gnd": {"type": "ground", "loc": "S2"}
        }

        # Recreate SiliconStep with updated config
        step_with_power = SiliconStep(self.config)
        step_with_power.platform = platform_mock

        # Reset captured config and call submit again
        capture_json_args.captured_config = None
        with mock.patch("builtins.print"):
            step_with_power.submit("/path/to/rtlil", dry_run=True)

        # Get new config with power entries
        config_with_power = capture_json_args.captured_config
        self.assertIsNotNone(config_with_power, "Config with power should have been captured")

        # Check power entries
        power = config_with_power["silicon"]["power"]
        self.assertIn("vdd", power)
        self.assertEqual(power["vdd"]["type"], "power")
        self.assertEqual(power["vdd"]["loc"], "N1")

        self.assertIn("gnd", power)
        self.assertEqual(power["gnd"]["type"], "ground")
        self.assertEqual(power["gnd"]["loc"], "S2")

    @mock.patch("chipflow_lib.steps.silicon.SiliconPlatform")
    @mock.patch("chipflow_lib.steps.silicon.importlib.metadata.version")
    @mock.patch("chipflow_lib.steps.silicon.subprocess.check_output")
    @mock.patch("chipflow_lib.steps.silicon.requests.post")
    @mock.patch("builtins.open", new_callable=mock.mock_open, read_data=b"rtlil content")
    def test_submit_success(self, mock_file_open, mock_post, mock_check_output,
                            mock_version, mock_platform_class):
        """Test submit method with successful submission"""
        # Setup mocks for git commands - return strings, not bytes
        mock_check_output.side_effect = [
            "abcdef\n",  # git rev-parse
            "M file.py"  # git status (dirty)
        ]

        # Setup version mocks
        mock_version.return_value = "1.0.0"

        # Setup response mock
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"build_id": "12345"}
        mock_post.return_value = mock_response

        # Setup platform mock
        platform_mock = mock_platform_class.return_value
        platform_mock._ports = {
            "port1": mock.MagicMock(
                pins=["1"],
                direction=mock.MagicMock(value="i")
            ),
            "port2": mock.MagicMock(
                pins=["2", "3"],
                direction=mock.MagicMock(value="o")
            )
        }

        # Add required environment variables
        with mock.patch.dict(os.environ, {
            "CHIPFLOW_API_KEY_ID": "api_key_id",
            "CHIPFLOW_API_KEY_SECRET": "api_key_secret"
        }):
            # Create SiliconStep with mocked platform
            step = SiliconStep(self.config)

            # Mock print and capture output
            with mock.patch("builtins.print") as mock_print:
                # Call submit
                step.submit("/path/to/rtlil")

                # Verify requests.post was called
                mock_post.assert_called_once()
                # Check auth was provided
                args, kwargs = mock_post.call_args
                self.assertEqual(kwargs["auth"], ("api_key_id", "api_key_secret"))
                # Check files were included
                self.assertIn("rtlil", kwargs["files"])
                self.assertIn("config", kwargs["files"])

                # Verify file was opened
                mock_file_open.assert_called_with("/path/to/rtlil", "rb")

                # Verify build URL was printed
                mock_print.assert_called_once()
                self.assertIn("build/12345", mock_print.call_args[0][0])

    @mock.patch("chipflow_lib.steps.silicon.SiliconPlatform")
    @mock.patch("chipflow_lib.steps.silicon.subprocess.check_output")
    @mock.patch("chipflow_lib.steps.silicon.importlib.metadata.version")
    @mock.patch("chipflow_lib.steps.silicon.requests.post")
    @mock.patch("builtins.open", new_callable=mock.mock_open, read_data=b"rtlil content")
    def test_submit_error(self, mock_file_open, mock_post, mock_version, mock_check_output, mock_platform_class):
        """Test submit method with API error response"""
        # Setup mocks for git commands - return strings, not bytes
        mock_check_output.side_effect = [
            "abcdef\n",  # git rev-parse
            ""           # git status (not dirty)
        ]

        # Setup version mocks
        mock_version.return_value = "1.0.0"

        # Setup response mock with error
        mock_response = mock.MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid project ID"}
        mock_response.request = mock.MagicMock()
        mock_response.request.url = "https://build.chipflow.org/api/builds"
        mock_response.request.headers = {"Authorization": "Basic xyz"}
        mock_response.headers = {"Content-Type": "application/json"}
        mock_post.return_value = mock_response

        # Setup platform mock
        platform_mock = mock_platform_class.return_value
        platform_mock._ports = {
            "port1": mock.MagicMock(
                pins=["1"],
                direction=mock.MagicMock(value="i")
            ),
        }

        # Add required environment variables
        with mock.patch.dict(os.environ, {
            "CHIPFLOW_API_KEY_ID": "api_key_id",
            "CHIPFLOW_API_KEY_SECRET": "api_key_secret"
        }):
            # Create SiliconStep with mocked platform
            step = SiliconStep(self.config)

            # Test for exception
            with self.assertRaises(ChipFlowError) as cm:
                step.submit("/path/to/rtlil")

            # Verify error message
            self.assertIn("Failed to submit design", str(cm.exception))

            # Verify requests.post was called
            mock_post.assert_called_once()


class TestSiliconTop(unittest.TestCase):
    def setUp(self):
        # Create basic config for tests
        self.config = {
            "chipflow": {
                "project_name": "test_project",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "top": {
                    "mock_component": "module.MockComponent"
                },
                "silicon": {
                    "package": "cf20",
                    "process": "ihp_sg13g2",
                    "debug": {
                        "heartbeat": True
                    }
                }
            }
        }

    def test_init(self):
        """Test SiliconTop initialization"""
        top = SiliconTop(self.config)
        self.assertEqual(top._config, self.config)

    @mock.patch("chipflow_lib.steps.silicon.top_interfaces")
    def test_elaborate(self, mock_top_interfaces):
        """Test SiliconTop elaborate method"""
        # Create mock platform
        platform = mock.MagicMock()
        # Ensure pinlock exists
        if not hasattr(platform, 'pinlock'):
            platform.pinlock = mock.MagicMock()
        # Configure port_map in a way that works for both dict and Pydantic model
        mock_port_map = {
            "comp1": {
                "iface1": {
                    "port1": mock.MagicMock(port_name="test_port")
                }
            }
        }
        # Set up pinlock.port_map in a way that works for both dict and Pydantic model
        if hasattr(platform.pinlock, 'port_map'):
            platform.pinlock.port_map = mock_port_map
        else:
            platform.pinlock.configure_mock(port_map=mock_port_map)

        platform.ports = {
            "test_port": mock.MagicMock(),
            "heartbeat": mock.MagicMock()
        }

        # Create mock components and interfaces
        mock_component = mock.MagicMock()
        mock_component.iface1.port1 = mock.MagicMock()
        mock_components = {"comp1": mock_component}

        # Setup top_interfaces mock
        mock_top_interfaces.return_value = (mock_components, {})

        # Create SiliconTop instance
        top = SiliconTop(self.config)

        # Call elaborate
        module = top.elaborate(platform)

        # Verify it's a Module
        self.assertIsInstance(module, Module)

        # Use the result to avoid UnusedElaboratable warning
        self.assertIsNotNone(module)

        # Verify platform methods were called
        platform.instantiate_ports.assert_called_once()

        # Verify port wiring
        platform.ports["test_port"].wire.assert_called_once()

        # Verify heartbeat was created (since debug.heartbeat is True)
        platform.request.assert_called_with("heartbeat")

    @mock.patch("chipflow_lib.steps.silicon.SiliconPlatform")
    @mock.patch("chipflow_lib.steps.silicon.top_interfaces")
    def test_elaborate_no_heartbeat(self, mock_top_interfaces, mock_platform_class):
        """Test SiliconTop elaborate without heartbeat"""
        # Config without heartbeat
        config_no_heartbeat = {
            "chipflow": {
                "project_name": "test_project",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "top": {
                    "mock_component": "module.MockComponent"
                },
                "silicon": {
                    "package": "cf20",
                    "process": "ihp_sg13g2",
                    "debug": {
                        "heartbeat": False
                    }
                }
            }
        }

        # Create mock platform
        platform = mock_platform_class.return_value
        # Ensure pinlock exists
        if not hasattr(platform, 'pinlock'):
            platform.pinlock = mock.MagicMock()
        # Configure port_map in a way that works for both dict and Pydantic model
        if hasattr(platform.pinlock, 'port_map'):
            platform.pinlock.port_map = {}
        else:
            platform.pinlock.configure_mock(port_map={})

        # Setup top_interfaces mock
        mock_top_interfaces.return_value = ({}, {})

        # Create SiliconTop instance with no heartbeat
        top = SiliconTop(config_no_heartbeat)

        # Call elaborate
        module = top.elaborate(platform)

        # Verify it's a Module
        self.assertIsInstance(module, Module)

        # Use the result to avoid UnusedElaboratable warning
        self.assertIsNotNone(module)

        # Verify platform methods were called
        platform.instantiate_ports.assert_called_once()

        # Verify heartbeat was not requested
        platform.request.assert_not_called()

