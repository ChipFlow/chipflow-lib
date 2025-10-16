# SPDX-License-Identifier: BSD-2-Clause
"""
Integration tests for ChipFlow CLI commands.

These tests execute actual CLI commands without mocking to ensure end-to-end functionality.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI commands using actual chipflow command execution"""

    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test execution
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(__file__).parent
        self.fixtures_dir = self.test_dir / "fixtures"

        # Copy mock.toml to temporary directory as chipflow.toml
        src_config = self.fixtures_dir / "mock.toml"
        dest_config = Path(self.temp_dir) / "chipflow.toml"
        shutil.copy(src_config, dest_config)

        # Set CHIPFLOW_ROOT to temporary directory
        os.environ["CHIPFLOW_ROOT"] = str(self.temp_dir)

    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def run_chipflow(self, args, expect_success=True):
        """
        Helper to run chipflow CLI command.

        Args:
            args: List of command arguments
            expect_success: Whether to expect the command to succeed

        Returns:
            CompletedProcess instance
        """
        result = subprocess.run(
            ["pdm", "run", "chipflow"] + args,
            capture_output=True,
            text=True,
            cwd=self.test_dir.parent
        )

        if expect_success and result.returncode != 0:
            print(f"Command failed: chipflow {' '.join(args)}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            self.fail(f"Expected command to succeed but it failed with code {result.returncode}")

        return result

    def test_cli_help(self):
        """Test that chipflow --help works"""
        result = self.run_chipflow(["--help"])
        self.assertIn("chipflow", result.stdout.lower())
        self.assertIn("silicon", result.stdout.lower())
        self.assertIn("sim", result.stdout.lower())
        self.assertIn("software", result.stdout.lower())
        self.assertIn("pin", result.stdout.lower())

    def test_cli_no_args_fails(self):
        """Test that chipflow with no arguments fails appropriately"""
        result = self.run_chipflow([], expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        # Should show usage or error about required command
        self.assertTrue(
            "required" in result.stderr.lower() or "usage" in result.stderr.lower(),
            f"Expected error about required command, got: {result.stderr}"
        )

    def test_pin_lock_help(self):
        """Test that chipflow pin lock --help works"""
        result = self.run_chipflow(["pin", "lock", "--help"])
        self.assertIn("lock", result.stdout.lower())

    def test_silicon_prepare_help(self):
        """Test that chipflow silicon prepare --help works"""
        result = self.run_chipflow(["silicon", "prepare", "--help"])
        self.assertIn("usage", result.stdout.lower())
        self.assertIn("silicon", result.stdout.lower())
        self.assertIn("prepare", result.stdout.lower())

    def test_silicon_submit_help(self):
        """Test that chipflow silicon submit --help works"""
        result = self.run_chipflow(["silicon", "submit", "--help"])
        self.assertIn("submit", result.stdout.lower())
        self.assertIn("dry-run", result.stdout.lower())
        self.assertIn("wait", result.stdout.lower())

    def test_sim_build_help(self):
        """Test that chipflow sim build --help works"""
        result = self.run_chipflow(["sim", "build", "--help"])
        self.assertIn("usage", result.stdout.lower())
        self.assertIn("sim", result.stdout.lower())
        self.assertIn("build", result.stdout.lower())

    def test_sim_run_help(self):
        """Test that chipflow sim run --help works"""
        result = self.run_chipflow(["sim", "run", "--help"])
        self.assertIn("run", result.stdout.lower())

    def test_sim_check_help(self):
        """Test that chipflow sim check --help works"""
        result = self.run_chipflow(["sim", "check", "--help"])
        self.assertIn("check", result.stdout.lower())

    def test_software_help(self):
        """Test that chipflow software --help works"""
        result = self.run_chipflow(["software", "--help"])
        self.assertIn("software", result.stdout.lower())

    def test_verbosity_flags(self):
        """Test that -v and -vv flags work"""
        # Single -v should work
        result = self.run_chipflow(["-v", "--help"])
        self.assertIn("chipflow", result.stdout.lower())

        # Double -v should work
        result = self.run_chipflow(["-v", "-v", "--help"])
        self.assertIn("chipflow", result.stdout.lower())

    def test_invalid_command(self):
        """Test that invalid command shows appropriate error"""
        result = self.run_chipflow(["invalid_command"], expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        # Should show error about invalid choice
        self.assertTrue(
            "invalid" in result.stderr.lower() or "choice" in result.stderr.lower(),
            f"Expected error about invalid command, got: {result.stderr}"
        )


if __name__ == "__main__":
    unittest.main()
