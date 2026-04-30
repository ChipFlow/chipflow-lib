# SPDX-License-Identifier: BSD-2-Clause

"""
ChipFlow authentication helper module.

Handles authentication for ChipFlow API with multiple fallback methods:
1. Environment variable CHIPFLOW_API_KEY
2. GitHub CLI token authentication (if gh is available)
3. OAuth 2.0 Device Flow
"""

import logging
import os
import subprocess
import sys
import time
import requests
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Exception raised when authentication fails."""
    pass


def get_credentials_file():
    """Get path to credentials file."""
    config_dir = Path.home() / ".config" / "chipflow"
    return config_dir / "credentials"


def save_api_key(api_key: str):
    """Save API key to credentials file."""
    creds_file = get_credentials_file()
    creds_file.parent.mkdir(parents=True, exist_ok=True)

    creds_data = {"api_key": api_key}
    creds_file.write_text(json.dumps(creds_data))
    creds_file.chmod(0o600)

    logger.info(f"API key saved to {creds_file}")


def load_saved_api_key():
    """Load API key from credentials file if it exists."""
    creds_file = get_credentials_file()
    if not creds_file.exists():
        return None

    try:
        creds_data = json.loads(creds_file.read_text())
        return creds_data.get("api_key")
    except (json.JSONDecodeError, KeyError):
        logger.warning(f"Invalid credentials file at {creds_file}")
        return None


def is_gh_authenticated():
    """Check if GitHub CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def get_gh_token():
    """Get GitHub token from gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def authenticate_with_github_token(api_origin: str, interactive: bool = True):
    """
    Authenticate using GitHub CLI token.

    Args:
        api_origin: ChipFlow API origin URL
        interactive: Whether to show interactive messages

    Returns:
        API key on success, None on failure
    """
    if interactive:
        print("🔍 Checking for GitHub CLI authentication...")

    if not is_gh_authenticated():
        if interactive:
            print("⚠️  GitHub CLI is not authenticated or not installed")
        return None

    gh_token = get_gh_token()
    if not gh_token:
        if interactive:
            print("⚠️  Could not get GitHub token from gh CLI")
        return None

    if interactive:
        print("🔑 Authenticating with GitHub token...")

    try:
        response = requests.post(
            f"{api_origin}/auth/github-token",
            json={"github_token": gh_token},
            timeout=10
        )

        if response.status_code == 200:
            try:
                api_key = response.json()["api_key"]
                save_api_key(api_key)
                if interactive:
                    print("✅ Authenticated using GitHub CLI!")
                return api_key
            except (KeyError, ValueError) as e:
                if interactive:
                    print("⚠️  Invalid response from authentication server")
                logger.debug(f"Invalid JSON response on success: {e}, body: {response.text[:200]}")
                return None
        else:
            error_code = ""
            try:
                body = response.json()
                error_code = body.get("error", "")
                error_msg = body.get("error_description", "Unknown error")
            except ValueError:
                error_msg = f"HTTP {response.status_code}"
                logger.debug(f"Non-JSON error response: {response.text[:200]}")

            if interactive:
                print(f"⚠️  GitHub token authentication failed: {error_msg}")
                if error_code == "missing_email":
                    # The server fetched the gh token but couldn't read the
                    # user's email — the token is missing the user:email
                    # scope. Tell the user the exact command to fix it,
                    # otherwise they fall through to device flow with no clue.
                    print(
                        "\n💡 Your `gh` CLI token is missing the `user:email` scope.\n"
                        "   Run this once and retry:\n"
                        "       gh auth refresh -s user:email"
                    )
            logger.debug(f"GitHub token auth failed: {response.status_code} - {error_msg}")
            return None

    except requests.exceptions.RequestException as e:
        if interactive:
            print(f"⚠️  Network error during GitHub token authentication: {e}")
        logger.debug(f"Network error during GitHub token auth: {e}")
        return None


def authenticate_with_device_flow(api_origin: str, interactive: bool = True):
    """
    Authenticate using OAuth 2.0 Device Flow.

    Args:
        api_origin: ChipFlow API origin URL
        interactive: Whether to show interactive messages

    Returns:
        API key on success, raises AuthenticationError on failure
    """
    if interactive:
        print("\n🌐 Starting device flow authentication...")

    try:
        # Step 1: Initiate device flow
        response = requests.post(f"{api_origin}/auth/device/init", timeout=10)
        response.raise_for_status()
        data = response.json()

        device_code = data["device_code"]
        user_code = data["user_code"]
        verification_uri = data["verification_uri"]
        interval = data["interval"]
        expires_in = data["expires_in"]

        # Step 2: Display instructions
        if interactive:
            print(f"\n📋 To authenticate, please visit:\n   {verification_uri}\n")
            print(f"   And enter this code:\n   {user_code}\n")
            print("⏳ Waiting for authorization...")

            # Try to open browser
            try:
                import webbrowser
                webbrowser.open(verification_uri)
            except Exception:
                pass  # Silently fail if browser opening doesn't work

        # Step 3: Poll for authorization
        max_attempts = expires_in // interval
        for attempt in range(max_attempts):
            time.sleep(interval)

            try:
                poll_response = requests.post(
                    f"{api_origin}/auth/device/poll",
                    json={"device_code": device_code},
                    timeout=10
                )

                if poll_response.status_code == 200:
                    # Success!
                    api_key = poll_response.json()["api_key"]
                    save_api_key(api_key)
                    if interactive:
                        print("\n✅ Authentication successful!")
                    return api_key

                elif poll_response.status_code == 202:
                    # Still pending
                    if interactive and sys.stdout.isatty():
                        print(".", end="", flush=True)
                    continue

                else:
                    # Error
                    error = poll_response.json()
                    error_desc = error.get("error_description", "Unknown error")
                    raise AuthenticationError(f"Device flow failed: {error_desc}")

            except requests.exceptions.RequestException as e:
                logger.debug(f"Poll request failed: {e}")
                continue

        raise AuthenticationError("Device flow authentication timed out")

    except requests.exceptions.RequestException as e:
        raise AuthenticationError(f"Network error during device flow: {e}")


def get_api_key(api_origin: str | None = None, interactive: bool = True, force_login: bool = False):
    """
    Get API key using the following priority:
    1. CHIPFLOW_API_KEY environment variable
    2. Saved credentials file (unless force_login is True)
    3. GitHub CLI token authentication
    4. Device flow authentication

    Args:
        api_origin: ChipFlow API origin URL (defaults to CHIPFLOW_API_ORIGIN env var or production)
        interactive: Whether to show interactive messages and prompts
        force_login: Force re-authentication even if credentials exist

    Returns:
        API key string

    Raises:
        AuthenticationError: If all authentication methods fail
    """
    if api_origin is None:
        api_origin = os.environ.get("CHIPFLOW_API_ORIGIN", "https://build.chipflow.com")

    # Method 1: Check environment variable
    api_key = os.environ.get("CHIPFLOW_API_KEY")
    if api_key:
        logger.debug("Using API key from CHIPFLOW_API_KEY environment variable")
        return api_key

    # Check for deprecated env var
    api_key = os.environ.get("CHIPFLOW_API_KEY_SECRET")
    if api_key:
        if interactive:
            print("⚠️  CHIPFLOW_API_KEY_SECRET is deprecated. Please use CHIPFLOW_API_KEY instead.")
        logger.warning("Using deprecated CHIPFLOW_API_KEY_SECRET environment variable")
        return api_key

    # Method 2: Check saved credentials (unless force_login)
    if not force_login:
        api_key = load_saved_api_key()
        if api_key:
            logger.debug("Using saved API key from credentials file")
            return api_key

    # Method 3: Try GitHub CLI token authentication
    api_key = authenticate_with_github_token(api_origin, interactive=interactive)
    if api_key:
        return api_key

    # Method 4: Fall back to device flow
    if interactive:
        print("\n💡 GitHub CLI not available. Using device flow authentication...")

    try:
        return authenticate_with_device_flow(api_origin, interactive=interactive)
    except AuthenticationError as e:
        raise AuthenticationError(
            f"All authentication methods failed. {e}\n\n"
            "Please either:\n"
            "  1. Set CHIPFLOW_API_KEY environment variable\n"
            "  2. Install and authenticate with GitHub CLI: gh auth login\n"
            "  3. Complete the device flow authorization"
        )


def logout():
    """Remove saved credentials."""
    creds_file = get_credentials_file()
    if creds_file.exists():
        creds_file.unlink()
        print(f"✅ Logged out. Credentials removed from {creds_file}")
    else:
        print("ℹ️  No saved credentials found")
