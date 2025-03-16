# SPDX-License-Identifier: BSD-2-Clause
import unittest
from unittest import mock

from chipflow_lib.steps.board import BoardStep
from chipflow_lib.steps.sim import SimStep
from chipflow_lib.steps.software import SoftwareStep


class TestBoardStep(unittest.TestCase):
    def test_board_step_initialization(self):
        """Test BoardStep initialization"""
        # Create mock objects
        mock_config = {"test": "config"}
        mock_platform = mock.Mock()

        # Initialize the step
        step = BoardStep(mock_config, mock_platform)

        # Check that attributes are set correctly
        self.assertEqual(step.platform, mock_platform)

    def test_board_step_build(self):
        """Test BoardStep build method"""
        # Create mock objects
        mock_config = {"test": "config"}
        mock_platform = mock.Mock()

        # Initialize the step
        step = BoardStep(mock_config, mock_platform)

        # Call build method
        step.build()

        # Check that platform.build was called
        mock_platform.build.assert_called_once()

    def test_board_step_cli(self):
        """Test BoardStep CLI methods"""
        # Create mock objects
        mock_config = {"test": "config"}
        mock_platform = mock.Mock()
        mock_parser = mock.Mock()
        mock_args = mock.Mock()

        # Initialize the step
        step = BoardStep(mock_config, mock_platform)

        # Patch the build method
        with mock.patch.object(step, 'build') as mock_build:
            # Call CLI methods
            step.build_cli_parser(mock_parser)
            step.run_cli(mock_args)

            # Check that build was called
            mock_build.assert_called_once()


class TestSimStep(unittest.TestCase):
    def test_sim_step_initialization(self):
        """Test SimStep initialization"""
        # Create mock objects
        mock_config = {"test": "config"}
        mock_platform = mock.Mock()

        # Initialize the step
        step = SimStep(mock_config, mock_platform)

        # Check that attributes are set correctly
        self.assertEqual(step.platform, mock_platform)
        self.assertIsNone(step.doit_build_module)

    @mock.patch('chipflow_lib.steps.sim.DoitMain')
    def test_sim_step_doit_build(self, mock_doit_main):
        """Test SimStep doit_build method"""
        # Create mock objects
        mock_config = {"test": "config"}
        mock_platform = mock.Mock()
        mock_module = mock.Mock()
        mock_doit_instance = mock.Mock()
        mock_doit_main.return_value = mock_doit_instance

        # Initialize the step
        step = SimStep(mock_config, mock_platform)
        step.doit_build_module = mock_module

        # Call doit_build method
        step.doit_build()

        # Check that DoitMain was initialized and run was called
        mock_doit_main.assert_called_once()
        mock_doit_instance.run.assert_called_once_with(["build_sim"])

    def test_sim_step_build(self):
        """Test SimStep build method"""
        # Create mock objects
        mock_config = {"test": "config"}
        mock_platform = mock.Mock()

        # Initialize the step
        step = SimStep(mock_config, mock_platform)

        # Patch the doit_build method
        with mock.patch.object(step, 'doit_build') as mock_doit_build:
            # Call build method
            step.build()

            # Check that platform.build and doit_build were called
            mock_platform.build.assert_called_once()
            mock_doit_build.assert_called_once()

    def test_sim_step_cli(self):
        """Test SimStep CLI methods"""
        # Create mock objects
        mock_config = {"test": "config"}
        mock_platform = mock.Mock()
        mock_parser = mock.Mock()
        mock_args = mock.Mock()

        # Initialize the step
        step = SimStep(mock_config, mock_platform)

        # Patch the build method
        with mock.patch.object(step, 'build') as mock_build:
            # Call CLI methods
            step.build_cli_parser(mock_parser)
            step.run_cli(mock_args)

            # Check that build was called
            mock_build.assert_called_once()


class TestSoftwareStep(unittest.TestCase):
    def test_software_step_initialization(self):
        """Test SoftwareStep initialization"""
        # Create mock objects
        mock_config = {"test": "config"}

        # Initialize the step
        step = SoftwareStep(mock_config)

        # Check that the doit_build_module is None
        self.assertIsNone(step.doit_build_module)

    @mock.patch('chipflow_lib.steps.software.DoitMain')
    def test_software_step_doit_build(self, mock_doit_main):
        """Test SoftwareStep doit_build method"""
        # Create mock objects
        mock_config = {"test": "config"}
        mock_module = mock.Mock()
        mock_doit_instance = mock.Mock()
        mock_doit_main.return_value = mock_doit_instance

        # Initialize the step
        step = SoftwareStep(mock_config)
        step.doit_build_module = mock_module

        # Call doit_build method
        step.doit_build()

        # Check that DoitMain was initialized and run was called
        mock_doit_main.assert_called_once()
        mock_doit_instance.run.assert_called_once_with(["build_software"])

    def test_software_step_build(self):
        """Test SoftwareStep build method"""
        # Create mock objects
        mock_config = {"test": "config"}

        # Initialize the step
        step = SoftwareStep(mock_config)

        # Patch the doit_build method
        with mock.patch.object(step, 'doit_build') as mock_doit_build:
            # Call build method
            step.build()

            # Check that doit_build was called
            mock_doit_build.assert_called_once()

    def test_software_step_cli(self):
        """Test SoftwareStep CLI methods"""
        # Create mock objects
        mock_config = {"test": "config"}
        mock_parser = mock.Mock()
        mock_args = mock.Mock()

        # Initialize the step
        step = SoftwareStep(mock_config)

        # Patch the build method
        with mock.patch.object(step, 'build') as mock_build:
            # Call CLI methods
            step.build_cli_parser(mock_parser)
            step.run_cli(mock_args)

            # Check that build was called
            mock_build.assert_called_once()