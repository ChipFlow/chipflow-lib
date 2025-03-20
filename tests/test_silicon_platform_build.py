# amaranth: UnusedElaboratable=no
# SPDX-License-Identifier: BSD-2-Clause

import os
import unittest
from unittest import mock

import tomli
from amaranth import Module


class TestSiliconPlatformBuild(unittest.TestCase):
    def setUp(self):
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))
        current_dir = os.path.dirname(__file__)
        customer_config = f"{current_dir}/fixtures/mock.toml"
        with open(customer_config, "rb") as f:
            self.config = tomli.load(f)

    def test_silicon_platform_init(self):
        """Test SiliconPlatform initialization"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform

        # Create platform
        platform = SiliconPlatform(self.config)

        # Check initialization
        self.assertEqual(platform._config, self.config)
        self.assertEqual(platform._ports, {})
        self.assertEqual(platform._files, {})

    def test_request_valid_port(self):
        """Test request method with a valid port name"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform

        # Create platform
        platform = SiliconPlatform(self.config)

        # Mock ports dictionary
        platform._ports = {
            "test_port": "port_value"
        }

        # Request the port
        result = platform.request("test_port")

        # Check result
        self.assertEqual(result, "port_value")

    def test_request_invalid_name(self):
        """Test request method with an invalid port name (contains $)"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform

        # Create platform
        platform = SiliconPlatform(self.config)

        # Request a port with $ in the name
        with self.assertRaises(NameError) as cm:
            platform.request("invalid$port")

        self.assertIn("Reserved character `$` used in pad name", str(cm.exception))

    def test_request_nonexistent_port(self):
        """Test request method with a port name that doesn't exist"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform

        # Create platform
        platform = SiliconPlatform(self.config)

        # Mock ports dictionary
        platform._ports = {
            "test_port": "port_value"
        }

        # Request a non-existent port
        with self.assertRaises(NameError) as cm:
            platform.request("nonexistent_port")

        self.assertIn("Pad `nonexistent_port` is not present in the pin lock", str(cm.exception))

    def test_add_file(self):
        """Test add_file method"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform

        # Create platform
        platform = SiliconPlatform(self.config)

        # Test with string content
        platform.add_file("test1.v", "module test1();endmodule")
        self.assertIn("test1.v", platform._files)
        self.assertEqual(platform._files["test1.v"], b"module test1();endmodule")

        # Test with file-like object
        file_obj = mock.Mock()
        file_obj.read.return_value = "module test2();endmodule"
        platform.add_file("test2.v", file_obj)
        self.assertIn("test2.v", platform._files)
        self.assertEqual(platform._files["test2.v"], b"module test2();endmodule")

        # Test with bytes content
        platform.add_file("test3.v", b"module test3();endmodule")
        self.assertIn("test3.v", platform._files)
        self.assertEqual(platform._files["test3.v"], b"module test3();endmodule")

    @mock.patch("chipflow_lib.platforms.silicon.rtlil.convert_fragment")
    @mock.patch("chipflow_lib.platforms.silicon.SiliconPlatform._prepare")
    @mock.patch("os.makedirs")
    @mock.patch("builtins.open", mock.mock_open())
    @mock.patch("subprocess.check_call")
    def test_build_mocked(self, mock_check_call, mock_makedirs, mock_prepare, mock_convert_fragment):
        """Test build method with mocks"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform

        # Set up mocks
        mock_prepare.return_value = "fragment"
        mock_convert_fragment.return_value = ("rtlil_text", None)

        # Create platform
        platform = SiliconPlatform(self.config)

        # Add some files
        platform._files = {
            "test.v": b"module test();endmodule",
        }

        # Create a test module
        m = Module()

        # Call build
        platform.build(m, name="test_top")

        # Check that the required methods were called
        mock_prepare.assert_called_once_with(m, "test_top")
        mock_convert_fragment.assert_called_once_with("fragment", "test_top")
        mock_makedirs.assert_called_once()
        mock_check_call.assert_called_once()