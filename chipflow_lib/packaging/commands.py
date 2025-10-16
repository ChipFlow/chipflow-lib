# SPDX-License-Identifier: BSD-2-Clause
"""
CLI commands for pin lock management.
"""

import inspect
import logging

from .utils import lock_pins

logger = logging.getLogger(__name__)


class PinCommand:
    """
    CLI command handler for pin-related operations.

    This class provides the command-line interface for managing
    pin allocations and lock files.
    """

    def __init__(self, config):
        """
        Initialize the pin command handler.

        Args:
            config: ChipFlow configuration object
        """
        self.config = config

    def build_cli_parser(self, parser):
        """
        Build the CLI parser for pin commands.

        Args:
            parser: argparse parser to add subcommands to
        """
        assert inspect.getdoc(self.lock) is not None
        action_argument = parser.add_subparsers(dest="action")
        action_argument.add_parser(
            "lock", help=inspect.getdoc(self.lock).splitlines()[0])  # type: ignore

    def run_cli(self, args):
        """
        Execute the CLI command.

        Args:
            args: Parsed command-line arguments
        """
        logger.debug(f"command {args}")
        if args.action == "lock":
            self.lock()

    def lock(self):
        """
        Lock the pin map for the design.

        Will attempt to reuse previous pin positions.
        """
        lock_pins(self.config)
