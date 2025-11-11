# SPDX-License-Identifier: BSD-2-Clause

import unittest
import json
import tempfile
from pathlib import Path
from unittest import mock

from chipflow.auth import (
    get_api_key,
    authenticate_with_github_token,
    authenticate_with_device_flow,
    is_gh_authenticated,
    get_gh_token,
    save_api_key,
    load_saved_api_key,
    logout,
    AuthenticationError,
)


class TestAuthHelpers(unittest.TestCase):
    """Test helper functions in auth module"""

    @mock.patch('chipflow.auth.subprocess.run')
    def test_is_gh_authenticated_success(self, mock_run):
        """Test checking if gh is authenticated - success case"""
        mock_run.return_value.returncode = 0
        self.assertTrue(is_gh_authenticated())
        mock_run.assert_called_once()

    @mock.patch('chipflow.auth.subprocess.run')
    def test_is_gh_authenticated_not_authenticated(self, mock_run):
        """Test checking if gh is authenticated - not authenticated"""
        mock_run.return_value.returncode = 1
        self.assertFalse(is_gh_authenticated())

    @mock.patch('chipflow.auth.subprocess.run')
    def test_is_gh_authenticated_not_installed(self, mock_run):
        """Test checking if gh is authenticated - not installed"""
        mock_run.side_effect = FileNotFoundError()
        self.assertFalse(is_gh_authenticated())

    @mock.patch('chipflow.auth.subprocess.run')
    def test_get_gh_token_success(self, mock_run):
        """Test getting GitHub token - success"""
        mock_run.return_value.stdout = "ghp_test123\n"
        token = get_gh_token()
        self.assertEqual(token, "ghp_test123")

    @mock.patch('chipflow.auth.subprocess.run')
    def test_get_gh_token_failure(self, mock_run):
        """Test getting GitHub token - failure"""
        mock_run.side_effect = FileNotFoundError()
        token = get_gh_token()
        self.assertIsNone(token)

    def test_save_and_load_api_key(self):
        """Test saving and loading API key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the credentials file path
            with mock.patch('chipflow.auth.get_credentials_file') as mock_creds_file:
                creds_file = Path(tmpdir) / "credentials"
                mock_creds_file.return_value = creds_file

                # Save API key
                test_key = "cf_test_12345"
                save_api_key(test_key)

                # Verify file exists and has correct permissions
                self.assertTrue(creds_file.exists())
                # Note: File permissions check skipped as it's platform-specific

                # Load API key
                loaded_key = load_saved_api_key()
                self.assertEqual(loaded_key, test_key)

    def test_load_api_key_no_file(self):
        """Test loading API key when file doesn't exist"""
        with mock.patch('chipflow.auth.get_credentials_file') as mock_creds_file:
            mock_creds_file.return_value = Path("/nonexistent/credentials")
            key = load_saved_api_key()
            self.assertIsNone(key)

    def test_logout(self):
        """Test logout removes credentials file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch('chipflow.auth.get_credentials_file') as mock_creds_file:
                creds_file = Path(tmpdir) / "credentials"
                mock_creds_file.return_value = creds_file

                # Create a credentials file
                creds_file.write_text(json.dumps({"api_key": "test"}))
                self.assertTrue(creds_file.exists())

                # Logout
                with mock.patch('builtins.print'):
                    logout()

                # File should be deleted
                self.assertFalse(creds_file.exists())


class TestGitHubTokenAuth(unittest.TestCase):
    """Test GitHub token authentication"""

    @mock.patch('chipflow.auth.save_api_key')
    @mock.patch('chipflow.auth.requests.post')
    @mock.patch('chipflow.auth.get_gh_token')
    @mock.patch('chipflow.auth.is_gh_authenticated')
    @mock.patch('builtins.print')
    def test_github_token_auth_success(
        self, mock_print, mock_is_gh, mock_get_token, mock_post, mock_save
    ):
        """Test successful GitHub token authentication"""
        mock_is_gh.return_value = True
        mock_get_token.return_value = "ghp_test123"
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"api_key": "cf_test_key"}

        api_key = authenticate_with_github_token("https://test.api", interactive=True)

        self.assertEqual(api_key, "cf_test_key")
        mock_save.assert_called_once_with("cf_test_key")
        mock_post.assert_called_once()

    @mock.patch('chipflow.auth.is_gh_authenticated')
    @mock.patch('builtins.print')
    def test_github_token_auth_not_authenticated(self, mock_print, mock_is_gh):
        """Test GitHub token auth when gh not authenticated"""
        mock_is_gh.return_value = False

        api_key = authenticate_with_github_token("https://test.api", interactive=True)

        self.assertIsNone(api_key)

    @mock.patch('chipflow.auth.requests.post')
    @mock.patch('chipflow.auth.get_gh_token')
    @mock.patch('chipflow.auth.is_gh_authenticated')
    @mock.patch('builtins.print')
    def test_github_token_auth_invalid_token(
        self, mock_print, mock_is_gh, mock_get_token, mock_post
    ):
        """Test GitHub token auth with invalid token"""
        mock_is_gh.return_value = True
        mock_get_token.return_value = "invalid_token"
        mock_post.return_value.status_code = 401
        mock_post.return_value.json.return_value = {
            "error": "invalid_token",
            "error_description": "Invalid GitHub token"
        }

        api_key = authenticate_with_github_token("https://test.api", interactive=True)

        self.assertIsNone(api_key)

    @mock.patch('chipflow.auth.requests.post')
    @mock.patch('chipflow.auth.get_gh_token')
    @mock.patch('chipflow.auth.is_gh_authenticated')
    @mock.patch('builtins.print')
    def test_github_token_auth_network_error(
        self, mock_print, mock_is_gh, mock_get_token, mock_post
    ):
        """Test GitHub token auth with network error"""
        import requests
        mock_is_gh.return_value = True
        mock_get_token.return_value = "ghp_test123"
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        api_key = authenticate_with_github_token("https://test.api", interactive=True)

        self.assertIsNone(api_key)


class TestDeviceFlowAuth(unittest.TestCase):
    """Test device flow authentication"""

    @mock.patch('chipflow.auth.save_api_key')
    @mock.patch('chipflow.auth.time.sleep')
    @mock.patch('chipflow.auth.requests.post')
    @mock.patch('builtins.print')
    def test_device_flow_success(self, mock_print, mock_post, mock_sleep, mock_save):
        """Test successful device flow authentication"""
        # Mock init response
        init_response = mock.Mock()
        init_response.status_code = 200
        init_response.json.return_value = {
            "device_code": "device123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://test.api/auth",
            "interval": 1,
            "expires_in": 60
        }

        # Mock poll response - success on first try
        poll_response = mock.Mock()
        poll_response.status_code = 200
        poll_response.json.return_value = {"api_key": "cf_test_key"}

        mock_post.side_effect = [init_response, poll_response]

        api_key = authenticate_with_device_flow("https://test.api", interactive=True)

        self.assertEqual(api_key, "cf_test_key")
        mock_save.assert_called_once_with("cf_test_key")

    @mock.patch('chipflow.auth.time.sleep')
    @mock.patch('chipflow.auth.requests.post')
    @mock.patch('builtins.print')
    def test_device_flow_pending_then_success(self, mock_print, mock_post, mock_sleep):
        """Test device flow with pending state then success"""
        # Mock init response
        init_response = mock.Mock()
        init_response.status_code = 200
        init_response.json.return_value = {
            "device_code": "device123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://test.api/auth",
            "interval": 1,
            "expires_in": 60
        }

        # Mock poll responses - pending, then success
        pending_response = mock.Mock()
        pending_response.status_code = 202
        pending_response.json.return_value = {
            "error": "authorization_pending"
        }

        success_response = mock.Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"api_key": "cf_test_key"}

        mock_post.side_effect = [init_response, pending_response, success_response]

        with mock.patch('chipflow.auth.save_api_key'):
            api_key = authenticate_with_device_flow("https://test.api", interactive=True)

        self.assertEqual(api_key, "cf_test_key")

    @mock.patch('chipflow.auth.time.sleep')
    @mock.patch('chipflow.auth.requests.post')
    @mock.patch('builtins.print')
    def test_device_flow_timeout(self, mock_print, mock_post, mock_sleep):
        """Test device flow timeout"""
        # Mock init response
        init_response = mock.Mock()
        init_response.status_code = 200
        init_response.json.return_value = {
            "device_code": "device123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://test.api/auth",
            "interval": 1,
            "expires_in": 2  # Very short timeout
        }

        # Mock poll response - always pending
        pending_response = mock.Mock()
        pending_response.status_code = 202
        pending_response.json.return_value = {
            "error": "authorization_pending"
        }

        mock_post.side_effect = [init_response, pending_response, pending_response, pending_response]

        with self.assertRaises(AuthenticationError) as ctx:
            authenticate_with_device_flow("https://test.api", interactive=True)

        self.assertIn("timed out", str(ctx.exception))


class TestGetAPIKey(unittest.TestCase):
    """Test the main get_api_key function with fallback logic"""

    def test_get_api_key_from_env_var(self):
        """Test getting API key from environment variable"""
        with mock.patch.dict('os.environ', {'CHIPFLOW_API_KEY': 'env_key'}):
            api_key = get_api_key(interactive=False)
            self.assertEqual(api_key, 'env_key')

    @mock.patch('chipflow.auth.load_saved_api_key')
    def test_get_api_key_from_saved_credentials(self, mock_load):
        """Test getting API key from saved credentials"""
        mock_load.return_value = "saved_key"
        with mock.patch.dict('os.environ', {}, clear=True):
            api_key = get_api_key(interactive=False)
            self.assertEqual(api_key, "saved_key")

    @mock.patch('chipflow.auth.authenticate_with_github_token')
    @mock.patch('chipflow.auth.load_saved_api_key')
    def test_get_api_key_gh_token_fallback(self, mock_load, mock_gh_auth):
        """Test fallback to GitHub token authentication"""
        mock_load.return_value = None
        mock_gh_auth.return_value = "gh_key"

        with mock.patch.dict('os.environ', {}, clear=True):
            api_key = get_api_key(interactive=True)
            self.assertEqual(api_key, "gh_key")

    @mock.patch('chipflow.auth.authenticate_with_device_flow')
    @mock.patch('chipflow.auth.authenticate_with_github_token')
    @mock.patch('chipflow.auth.load_saved_api_key')
    def test_get_api_key_device_flow_fallback(
        self, mock_load, mock_gh_auth, mock_device_flow
    ):
        """Test fallback to device flow authentication"""
        mock_load.return_value = None
        mock_gh_auth.return_value = None
        mock_device_flow.return_value = "device_key"

        with mock.patch.dict('os.environ', {}, clear=True):
            with mock.patch('builtins.print'):
                api_key = get_api_key(interactive=True)
                self.assertEqual(api_key, "device_key")

    @mock.patch('chipflow.auth.authenticate_with_device_flow')
    @mock.patch('chipflow.auth.authenticate_with_github_token')
    @mock.patch('chipflow.auth.load_saved_api_key')
    def test_get_api_key_all_methods_fail(
        self, mock_load, mock_gh_auth, mock_device_flow
    ):
        """Test when all authentication methods fail"""
        mock_load.return_value = None
        mock_gh_auth.return_value = None
        mock_device_flow.side_effect = AuthenticationError("All methods failed")

        with mock.patch.dict('os.environ', {}, clear=True):
            with mock.patch('builtins.print'):
                with self.assertRaises(AuthenticationError) as ctx:
                    get_api_key(interactive=True)
                self.assertIn("All authentication methods failed", str(ctx.exception))

    @mock.patch('chipflow.auth.load_saved_api_key')
    def test_get_api_key_force_login_ignores_saved(self, mock_load):
        """Test force_login parameter ignores saved credentials"""
        mock_load.return_value = "saved_key"

        with mock.patch.dict('os.environ', {}, clear=True):
            with mock.patch('chipflow.auth.authenticate_with_github_token') as mock_gh:
                mock_gh.return_value = "new_key"
                api_key = get_api_key(interactive=True, force_login=True)
                self.assertEqual(api_key, "new_key")
                # Should not have called load_saved_api_key due to force_login
                mock_load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
