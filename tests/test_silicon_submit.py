# SPDX-License-Identifier: BSD-2-Clause

import unittest
from unittest import mock
from argparse import Namespace
from pathlib import Path
import tempfile
import os

from chipflow.platform.silicon_step import SiliconStep


class TestSiliconSubmitBrowserPrompt(unittest.TestCase):
    """Test the browser prompt functionality in silicon submit"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(__file__).parent
        self.fixtures_dir = self.test_dir / "fixtures"

        # Set CHIPFLOW_ROOT to temporary directory
        os.environ["CHIPFLOW_ROOT"] = str(self.temp_dir)

    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    @mock.patch('chipflow.packaging.load_pinlock')
    @mock.patch('chipflow.platform.silicon_step.webbrowser.open')
    @mock.patch('builtins.input')
    @mock.patch('sys.stdout.isatty')
    @mock.patch('chipflow.platform.silicon_step.subprocess.check_output')
    def test_browser_prompt_yes(self, mock_subprocess, mock_isatty, mock_input, mock_webbrowser, mock_load_pinlock):
        """Test that browser opens when user responds 'yes'"""
        mock_isatty.return_value = True
        mock_input.return_value = 'yes'
        mock_subprocess.return_value = 'test123\n'

        # Mock pinlock
        mock_pinlock = mock.MagicMock()
        mock_pinlock.model_dump_json.return_value = '{}'
        mock_load_pinlock.return_value = mock_pinlock

        # Create a mock SiliconStep instance
        with mock.patch('chipflow.platform.silicon_step.SiliconPlatform'):
            config = mock.MagicMock()
            config.chipflow.silicon = True
            config.chipflow.project_name = 'test_project'
            step = SiliconStep(config)
            step._build_url = "https://build.chipflow.org/build/test123"
            step.platform._ports = {}

            # Mock the submit method dependencies
            with mock.patch.object(step, 'prepare', return_value='/tmp/test.il'):
                with mock.patch('builtins.open', mock.mock_open(read_data=b'')):
                    with mock.patch('chipflow.platform.silicon_step.requests.post') as mock_post:
                        # Mock successful submission
                        mock_response = mock.MagicMock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = {'build_id': 'test123'}
                        mock_post.return_value = mock_response

                        # Mock get_api_key
                        with mock.patch('chipflow.platform.silicon_step.get_api_key', return_value='test_key'):
                            # Mock exit to prevent test from exiting
                            with mock.patch('chipflow.platform.silicon_step.exit') as mock_exit:
                                args = Namespace(dry_run=False, wait=False)
                                step._chipflow_api_key = 'test_key'

                                # Call submit with mocked dependencies
                                step.submit('/tmp/test.il', args)

                                # Verify webbrowser.open was called
                                mock_webbrowser.assert_called_once_with("https://build.chipflow.org/build/test123")
                                mock_exit.assert_called_once_with(0)

    @mock.patch('chipflow.packaging.load_pinlock')
    @mock.patch('chipflow.platform.silicon_step.webbrowser.open')
    @mock.patch('builtins.input')
    @mock.patch('sys.stdout.isatty')
    @mock.patch('chipflow.platform.silicon_step.subprocess.check_output')
    def test_browser_prompt_no(self, mock_subprocess, mock_isatty, mock_input, mock_webbrowser, mock_load_pinlock):
        """Test that browser doesn't open when user responds 'no'"""
        mock_isatty.return_value = True
        mock_input.return_value = 'no'
        mock_subprocess.return_value = 'test123\n'

        # Mock pinlock
        mock_pinlock = mock.MagicMock()
        mock_pinlock.model_dump_json.return_value = '{}'
        mock_load_pinlock.return_value = mock_pinlock

        # Create a mock SiliconStep instance
        with mock.patch('chipflow.platform.silicon_step.SiliconPlatform'):
            config = mock.MagicMock()
            config.chipflow.silicon = True
            config.chipflow.project_name = 'test_project'
            step = SiliconStep(config)
            step._build_url = "https://build.chipflow.org/build/test123"
            step.platform._ports = {}

            # Mock the submit method dependencies
            with mock.patch.object(step, 'prepare', return_value='/tmp/test.il'):
                with mock.patch('builtins.open', mock.mock_open(read_data=b'')):
                    with mock.patch('chipflow.platform.silicon_step.requests.post') as mock_post:
                        # Mock successful submission
                        mock_response = mock.MagicMock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = {'build_id': 'test123'}
                        mock_post.return_value = mock_response

                        # Mock get_api_key
                        with mock.patch('chipflow.platform.silicon_step.get_api_key', return_value='test_key'):
                            # Mock exit to prevent test from exiting
                            with mock.patch('chipflow.platform.silicon_step.exit'):
                                args = Namespace(dry_run=False, wait=False)
                                step._chipflow_api_key = 'test_key'

                                # Call submit with mocked dependencies
                                step.submit('/tmp/test.il', args)

                                # Verify webbrowser.open was NOT called
                                mock_webbrowser.assert_not_called()

    @mock.patch('chipflow.packaging.load_pinlock')
    @mock.patch('chipflow.platform.silicon_step.webbrowser.open')
    @mock.patch('builtins.input')
    @mock.patch('sys.stdout.isatty')
    @mock.patch('chipflow.platform.silicon_step.subprocess.check_output')
    def test_browser_prompt_not_tty(self, mock_subprocess, mock_isatty, mock_input, mock_webbrowser, mock_load_pinlock):
        """Test that browser prompt is skipped when not in a TTY"""
        mock_isatty.return_value = False
        mock_subprocess.return_value = 'test123\n'

        # Mock pinlock
        mock_pinlock = mock.MagicMock()
        mock_pinlock.model_dump_json.return_value = '{}'
        mock_load_pinlock.return_value = mock_pinlock

        # Create a mock SiliconStep instance
        with mock.patch('chipflow.platform.silicon_step.SiliconPlatform'):
            config = mock.MagicMock()
            config.chipflow.silicon = True
            config.chipflow.project_name = 'test_project'
            step = SiliconStep(config)
            step._build_url = "https://build.chipflow.org/build/test123"
            step.platform._ports = {}

            # Mock the submit method dependencies
            with mock.patch.object(step, 'prepare', return_value='/tmp/test.il'):
                with mock.patch('builtins.open', mock.mock_open(read_data=b'')):
                    with mock.patch('chipflow.platform.silicon_step.requests.post') as mock_post:
                        # Mock successful submission
                        mock_response = mock.MagicMock()
                        mock_response.status_code = 200
                        mock_response.json.return_value = {'build_id': 'test123'}
                        mock_post.return_value = mock_response

                        # Mock get_api_key
                        with mock.patch('chipflow.platform.silicon_step.get_api_key', return_value='test_key'):
                            # Mock exit to prevent test from exiting
                            with mock.patch('chipflow.platform.silicon_step.exit'):
                                args = Namespace(dry_run=False, wait=False)
                                step._chipflow_api_key = 'test_key'

                                # Call submit with mocked dependencies
                                step.submit('/tmp/test.il', args)

                                # Verify input was NOT called (no prompt in non-TTY)
                                mock_input.assert_not_called()
                                # Verify webbrowser.open was NOT called
                                mock_webbrowser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
