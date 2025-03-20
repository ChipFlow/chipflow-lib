# amaranth: UnusedElaboratable=no
# SPDX-License-Identifier: BSD-2-Clause

import os
import unittest
from unittest import mock

import tomli
from amaranth import Signal


class TestSimPlatform(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Set up environment variable
        self.original_chipflow_root = os.environ.get("CHIPFLOW_ROOT")
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))

        # Load config for use in tests
        current_dir = os.path.dirname(__file__)
        customer_config = f"{current_dir}/fixtures/mock.toml"
        with open(customer_config, "rb") as f:
            self.config = tomli.load(f)

    def tearDown(self):
        """Clean up environment"""
        if self.original_chipflow_root:
            os.environ["CHIPFLOW_ROOT"] = self.original_chipflow_root
        else:
            os.environ.pop("CHIPFLOW_ROOT", None)

    def test_sim_platform_init(self):
        """Test SimPlatform initialization"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.sim import SimPlatform

        # Create platform
        platform = SimPlatform()

        # Check initialization
        self.assertEqual(platform.build_dir, os.path.join(os.environ['CHIPFLOW_ROOT'], 'build', 'sim'))
        self.assertEqual(platform.extra_files, {})
        self.assertEqual(platform.sim_boxes, {})

        # Check signals
        self.assertIsInstance(platform.clk, Signal)
        self.assertIsInstance(platform.rst, Signal)
        self.assertIsInstance(platform.buttons, Signal)
        self.assertEqual(len(platform.buttons), 2)

    def test_add_file(self):
        """Test add_file method"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.sim import SimPlatform

        # Create platform
        platform = SimPlatform()

        # Test with string content
        platform.add_file("test.v", "module test(); endmodule")
        self.assertIn("test.v", platform.extra_files)
        self.assertEqual(platform.extra_files["test.v"], "module test(); endmodule")

        # Test with file-like object
        file_obj = mock.Mock()
        file_obj.read.return_value = "module test2(); endmodule"
        platform.add_file("test2.v", file_obj)
        self.assertIn("test2.v", platform.extra_files)
        self.assertEqual(platform.extra_files["test2.v"], "module test2(); endmodule")