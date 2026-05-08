# SPDX-License-Identifier: BSD-2-Clause
"""
CLI commands for pin lock management.
"""

import inspect
import logging
from pathlib import Path

from .utils import lock_pins, swap_pins, load_pinlock
from .render import render_text, render_svg

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
        assert inspect.getdoc(self.swap) is not None
        assert inspect.getdoc(self.show) is not None
        action_argument = parser.add_subparsers(dest="action")

        action_argument.add_parser(
            "lock", help=inspect.getdoc(self.lock).splitlines()[0])  # type: ignore

        swap_parser = action_argument.add_parser(
            "swap", help=inspect.getdoc(self.swap).splitlines()[0])  # type: ignore
        swap_parser.add_argument("pin_a", type=int, help="first pin number")
        swap_parser.add_argument("pin_b", type=int, help="second pin number")

        show_parser = action_argument.add_parser(
            "show", help=inspect.getdoc(self.show).splitlines()[0])  # type: ignore
        show_parser.add_argument(
            "--format", "-f",
            choices=("text", "svg"), default="text",
            help="output format (default: text)"
        )
        show_parser.add_argument(
            "--output", "-o", type=Path, default=None,
            help="write to file instead of stdout"
        )

    def run_cli(self, args):
        """
        Execute the CLI command.

        Args:
            args: Parsed command-line arguments
        """
        logger.debug(f"command {args}")
        if args.action == "lock":
            self.lock()
        elif args.action == "swap":
            self.swap(args.pin_a, args.pin_b)
        elif args.action == "show":
            self.show(format=args.format, output=args.output)

    def lock(self):
        """
        Lock the pin map for the design.

        Will attempt to reuse previous pin positions.
        """
        lock_pins(self.config)

    def swap(self, pin_a: int, pin_b: int):
        """
        Swap two pin assignments in pins.lock.

        Both pins must currently be allocated to user ports; bringup
        pins (clock, reset, power, heartbeat, JTAG) are package-defined
        and cannot be swapped.
        """
        swap_pins(pin_a, pin_b)

    def show(self, format: str = "text", output: Path | None = None):
        """
        Show the current pin allocation from pins.lock.

        Text format works for any package type. SVG format renders a
        package layout for perimeter packages (Quad/Block).
        """
        lockfile = load_pinlock()
        if format == "svg":
            rendered = render_svg(lockfile)
        else:
            rendered = render_text(lockfile)
        if output is not None:
            output.write_text(rendered)
            print(f"Wrote {output}")
        else:
            print(rendered, end='')
