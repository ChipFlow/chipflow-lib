# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import inspect
import importlib
import argparse
import tomli

from . import ChipFlowError


def _get_cls_by_reference(reference, context):
    module_ref, _, class_ref = reference.partition(":")
    try:
        module_obj = importlib.import_module(module_ref)
    except ModuleNotFoundError as e:
        raise ChipFlowError(f"Module `{module_ref}` referenced by {context} is not found")
    try:
        return getattr(module_obj, class_ref)
    except AttributeError as e:
        raise ChipFlowError(f"Module `{module_ref}` referenced by {context} does not define "
                            f"`{class_ref}`") from None


def _ensure_chipflow_root():
    if "CHIPFLOW_ROOT" not in os.environ:
        os.environ["CHIPFLOW_ROOT"] = os.getcwd()
    if os.environ["CHIPFLOW_ROOT"] not in sys.path:
        sys.path.append(os.environ["CHIPFLOW_ROOT"])
    return os.environ["CHIPFLOW_ROOT"]


def _parse_config():
    chipflow_root = _ensure_chipflow_root()
    config_file = f"{chipflow_root}/chipflow.toml"

    # TODO: Add better validation/errors for loading chipflow.toml
    with open(config_file, "rb") as f:
        return tomli.load(f)


def run(argv=sys.argv[1:]):
    config = _parse_config()

    steps = {}
    for step_name, step_reference in config["chipflow"]["steps"].items():
        step_cls = _get_cls_by_reference(step_reference, context=f"step `{step_name}`")
        try:
            steps[step_name] = step_cls(config)
        except Exception:
            raise ChipFlowError(f"Encountered error while initializing step `{step_name}` "
                                f"using `{step_reference}`")

    parser = argparse.ArgumentParser()
    step_argument = parser.add_subparsers(dest="step", required=True)
    for step_name, step_cls in steps.items():
        step_subparser = step_argument.add_parser(step_name, help=inspect.getdoc(step_cls))
        try:
            step_cls.build_cli_parser(step_subparser)
        except Exception:
            raise ChipFlowError(f"Encountered error while building CLI argument parser for "
                                f"step `{step_name}`")

    args = parser.parse_args(argv)
    try:
        steps[args.step].run_cli(args)
    except Exception:
        raise ChipFlowError(f"Encountered error while running CLI for step `{args.step}`")


if __name__ == '__main__':
    run()
