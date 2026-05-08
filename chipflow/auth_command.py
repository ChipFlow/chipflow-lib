# SPDX-License-Identifier: BSD-2-Clause

"""
ChipFlow authentication command for CLI.

Provides `chipflow login` and `chipflow logout` commands.
"""

import sys
from .auth import get_api_key, logout as auth_logout, AuthenticationError
from .utils import ChipFlowError


class AuthCommand:
    """Authentication management for ChipFlow."""

    def __init__(self, config):
        """Initialize the auth command.

        Args:
            config: ChipFlow configuration object
        """
        self.config = config

    def build_cli_parser(self, parser):
        """Build CLI argument parser for auth command."""
        subparsers = parser.add_subparsers(dest="action", required=True)

        # Login command
        login_parser = subparsers.add_parser(
            "login",
            help="Authenticate with ChipFlow API"
        )
        login_parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-authentication even if already logged in"
        )

        # Logout command
        subparsers.add_parser(
            "logout",
            help="Remove saved credentials"
        )

    def run_cli(self, args):
        """Execute the auth command based on parsed arguments."""
        if args.action == "login":
            self._login(force=args.force)
        elif args.action == "logout":
            self._logout()
        else:
            raise ChipFlowError(f"Unknown auth action: {args.action}")

    def _login(self, force=False):
        """Perform login/authentication.

        `chipflow auth login` always re-authenticates against the configured
        origin — the cached credential is never reused, otherwise the user
        gets a stale key bound to a different origin and `submit` 401s.
        The `--force` flag is kept for clarity but is effectively the default.
        """
        import os
        from .auth import DEFAULT_API_ORIGIN

        api_origin = os.environ.get("CHIPFLOW_API_ORIGIN", DEFAULT_API_ORIGIN)

        print(f"🔐 Authenticating with ChipFlow API ({api_origin})...")

        try:
            api_key = get_api_key(
                api_origin=api_origin,
                interactive=True,
                force_login=True,
            )
            print("\n✅ Successfully authenticated!")
            print(f"   API key: {api_key[:20]}...")
            print("\n💡 You can now use `chipflow silicon submit` to submit designs")

        except AuthenticationError as e:
            print(f"\n❌ Authentication failed: {e}")
            sys.exit(1)

    def _logout(self):
        """Perform logout."""
        auth_logout()
