# SPDX-License-Identifier: BSD-2-Clause
import argparse
import inspect
import sys
import traceback
import logging

from pprint import pformat

from . import (
    ChipFlowError,
    _get_cls_by_reference,
    _parse_config,
)
from .pin_lock import PinCommand


logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class UnexpectedError(ChipFlowError):
    pass


def run(argv=sys.argv[1:]):
    config = _parse_config()

    commands = {}
    commands["pin"] = PinCommand(config)

    for step_name, step_reference in config["chipflow"]["steps"].items():
        step_cls = _get_cls_by_reference(step_reference, context=f"step `{step_name}`")
        try:
            commands[step_name] = step_cls(config)
        except Exception:
            raise ChipFlowError(f"Encountered error while initializing step `{step_name}` "
                              f"using `{step_reference}`")

    parser = argparse.ArgumentParser(
        prog="chipflow",
        description="Command line tool for interacting with the ChipFlow platform")

    parser.add_argument(
        "--verbose", "-v",
        dest="log_level",
        action="append_const",
        const=10,
        help="increase verbosity of messages; can be supplied multiple times to increase verbosity"
    )

    command_argument = parser.add_subparsers(dest="command", required=True)
    for command_name, command in commands.items():
        command_subparser = command_argument.add_parser(command_name, help=inspect.getdoc(command))
        try:
            command.build_cli_parser(command_subparser)
        except Exception:
            raise ChipFlowError(f"Encountered error while building CLI argument parser for "
                              f"step `{command_name}`")

    # each verbose flag increases versbosity (e.g. -v -v, -vv, --verbose --verbose)
    # cute trick using append_const and summing
    args = parser.parse_args(argv)
    if args.log_level:
        log_level = max(logging.DEBUG, logging.WARNING - sum(args.log_level))
        logging.getLogger().setLevel(log_level)

    try:
        try:
            commands[args.command].run_cli(args)
        except ChipFlowError:
            raise
        except Exception as e:
            # convert to ChipFlowError so all handling is same.
            raise UnexpectedError(
                f"Unexpected error, please report to ChipFlow:\n"
                f"args =\n{pformat(args)}\n"
                f"traceback =\n{''.join(traceback.format_exception(e))}"
            ) from e
    except ChipFlowError as e:
        cmd = args.command
        if hasattr(args, "action"):
            cmd += f" {args.action}"
        print(f"Error while executing `{cmd}`: {e}")
        exit(1)
