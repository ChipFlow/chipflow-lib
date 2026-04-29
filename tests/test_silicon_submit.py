# SPDX-License-Identifier: BSD-2-Clause

import io
import json
import unittest
import zipfile
from unittest import mock
from argparse import Namespace
from pathlib import Path
import tempfile
import os

from chipflow.platform.silicon_step import SiliconStep, _build_bundle_zip


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
            step._build_url = "https://build.chipflow.com/build/test123"
            step.platform._ports = {}

            # Mock the submit method dependencies
            with mock.patch.object(step, 'prepare', return_value='/tmp/test.il'), \
                    mock.patch('chipflow.platform.silicon_step._build_bundle_zip', return_value=b'fake-bundle'):
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
                                mock_webbrowser.assert_called_once_with("https://build.chipflow.com/build/test123")
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
            step._build_url = "https://build.chipflow.com/build/test123"
            step.platform._ports = {}

            # Mock the submit method dependencies
            with mock.patch.object(step, 'prepare', return_value='/tmp/test.il'), \
                    mock.patch('chipflow.platform.silicon_step._build_bundle_zip', return_value=b'fake-bundle'):
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
            step._build_url = "https://build.chipflow.com/build/test123"
            step.platform._ports = {}

            # Mock the submit method dependencies
            with mock.patch.object(step, 'prepare', return_value='/tmp/test.il'), \
                    mock.patch('chipflow.platform.silicon_step._build_bundle_zip', return_value=b'fake-bundle'):
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


class TestBuildBundleZip(unittest.TestCase):
    """Tests for the _build_bundle_zip helper."""

    def test_manifest_and_layout(self):
        with tempfile.TemporaryDirectory() as td:
            rtlil_path = Path(td) / "top.il"
            rtlil_path.write_text("module top(); endmodule\n")
            config = '{"pins": []}'

            blob = _build_bundle_zip(rtlil_path, config, "my_project")

            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                names = set(zf.namelist())
                self.assertEqual(names, {"manifest.json", "top.il", "pins.lock"})

                manifest = json.loads(zf.read("manifest.json"))
                self.assertEqual(manifest["version"], "1")
                self.assertEqual(manifest["project"], "my_project")
                self.assertEqual(manifest["design_file"], "top.il")
                self.assertEqual(manifest["pins_lock_file"], "pins.lock")

                self.assertEqual(zf.read("top.il").decode(), "module top(); endmodule\n")
                self.assertEqual(zf.read("pins.lock").decode(), config)

    def test_uses_real_rtlil_filename(self):
        """Bundle preserves the source rtlil filename (not a fixed string)."""
        with tempfile.TemporaryDirectory() as td:
            rtlil_path = Path(td) / "weird_name.rtlil"
            rtlil_path.write_text("x")
            blob = _build_bundle_zip(rtlil_path, "{}", "p")
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                self.assertIn("weird_name.rtlil", zf.namelist())
                manifest = json.loads(zf.read("manifest.json"))
                self.assertEqual(manifest["design_file"], "weird_name.rtlil")


class TestSiliconSubmitBundlePost(unittest.TestCase):
    """The submit() path posts a single 'bundle' multipart part."""

    @mock.patch('chipflow.packaging.load_pinlock')
    @mock.patch('chipflow.platform.silicon_step.subprocess.check_output')
    def test_submit_sends_single_bundle_part(self, mock_subprocess, mock_load_pinlock):
        mock_subprocess.return_value = 'test123\n'
        mock_pinlock = mock.MagicMock()
        mock_pinlock.model_dump_json.return_value = '{}'
        mock_load_pinlock.return_value = mock_pinlock

        with mock.patch('chipflow.platform.silicon_step.SiliconPlatform'):
            config = mock.MagicMock()
            config.chipflow.silicon = True
            config.chipflow.project_name = 'test_project'
            step = SiliconStep(config)
            step.platform._ports = {}

            with mock.patch.object(step, 'prepare', return_value='/tmp/test.il'), \
                    mock.patch('chipflow.platform.silicon_step._build_bundle_zip',
                               return_value=b'fake-bundle-bytes'), \
                    mock.patch('chipflow.platform.silicon_step.requests.post') as mock_post, \
                    mock.patch('chipflow.platform.silicon_step.get_api_key', return_value='k'), \
                    mock.patch('chipflow.platform.silicon_step.exit'), \
                    mock.patch('sys.stdout.isatty', return_value=False):
                mock_post.return_value = mock.MagicMock(
                    status_code=200, json=lambda: {'build_id': 'b1'})
                step._chipflow_api_key = 'k'
                step.submit('/tmp/test.il', Namespace(dry_run=False, wait=False))

            files = mock_post.call_args.kwargs["files"]
            self.assertEqual(set(files.keys()), {"bundle"})
            filename, payload, content_type = files["bundle"]
            self.assertEqual(filename, "bundle.zip")
            self.assertEqual(payload, b'fake-bundle-bytes')
            self.assertEqual(content_type, "application/zip")


if __name__ == "__main__":
    unittest.main()
