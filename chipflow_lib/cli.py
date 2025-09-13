# SPDX-License-Identifier: BSD-2-Clause

import argparse
import inspect
import sys
import traceback
import logging

from pathlib import Path
from pprint import pformat

from . import (
    ChipFlowError,
    _get_cls_by_reference,
    _parse_config,
)
from ._pin_lock import PinCommand

class UnexpectedError(ChipFlowError):
    pass

log_level = logging.WARNING


DEFAULT_STEPS = {
    "silicon": "chipflow_lib.steps.silicon:SiliconStep",
    "sim": "chipflow_lib.steps.sim:SimStep",
    "software": "chipflow_lib.steps.software:SoftwareStep"
}


def run(argv=sys.argv[1:]):
    config = _parse_config()

    commands = {}
    commands["pin"] = PinCommand(config)

    if config.chipflow.steps:
        steps = DEFAULT_STEPS |config.chipflow.steps
    else:
        steps = DEFAULT_STEPS

    for step_name, step_reference in steps.items():
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
        action="count",
        default=0,
        help="increase verbosity of messages; can be supplied multiple times to increase verbosity"
    )
    parser.add_argument(
        "--log-file", help=argparse.SUPPRESS,
        default=None, action="store"
    )


    command_argument = parser.add_subparsers(dest="command", required=True)
    for command_name, command in commands.items():
        command_subparser = command_argument.add_parser(command_name, help=inspect.getdoc(command))
        try:
            command.build_cli_parser(command_subparser)
        except Exception:
            raise ChipFlowError(f"Encountered error while building CLI argument parser for "
                              f"step `{command_name}`")

    args = parser.parse_args(argv)
    global log_level
    log_level = max(logging.WARNING - args.log_level * 10, 0)
    logging.getLogger().setLevel(logging.NOTSET)

    # Add stdout handler, with level as set
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    formatter = logging.Formatter('%(name)-13s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

    #Log to file with DEBUG level
    if args.log_file:
        filename = Path(args.log_file).absolute()
        print(f"> Logging to {str(filename)}")
        fh = logging.FileHandler(filename)
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logging.getLogger().addHandler(fh)

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
