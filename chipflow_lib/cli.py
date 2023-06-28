# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import inspect
import importlib
import argparse
import tomli
import jsonschema

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


config_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://chipflow.io/meta/chipflow.toml.schema.json",
    "title": "chipflow.toml",
    "type": "object",
    "required": [
        "chipflow"
    ],
    "properties": {
        "chipflow": {
            "type": "object",
            "required": [
                "steps",
                "silicon"
            ],
            "properties": {
                "project_id": {
                    "type": "integer",
                },
                "steps": {
                    "type": "object",
                },
                "silicon": {
                    "type": "object",
                    "required": [
                        "process",
                        "pad_ring",
                        "pads",
                    ],
                    "properties": {
                        "process": {
                            "enum": ["sky130", "gf180", "customer1"]
                        },
                        "pad_ring": {
                            "enum": ["caravel", "cf20"]
                        },
                        "pads": {
                            "type": "object",
                            "minProperties": 1,
                            "patternProperties": {
                                "": {
                                    "type": "object",
                                    "required": [
                                        "type",
                                        "loc",
                                    ],
                                    "properties": {
                                        "type": {
                                            "enum": ["io", "i", "o", "oe", "clk"]
                                        },
                                        "loc": {
                                            "type": "string",
                                            "pattern": "^[0-9]+$"
                                        },
                                    }
                                }
                            }
                        },
                    }
                },
            },
        }
    }
}


def _parse_config():
    chipflow_root = _ensure_chipflow_root()
    config_file = f"{chipflow_root}/chipflow.toml"
    with open(config_file, "rb") as f:
        config_dict = tomli.load(f)

    try:
        jsonschema.validate(config_dict, config_schema)
        return config_dict
    except jsonschema.ValidationError as e:
        raise ChipFlowError(f"Syntax error in `chipflow.toml` at `{'.'.join(e.path)}`: {e.message}")


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
    except ChipFlowError:
        raise
    except Exception:
        raise ChipFlowError(f"Encountered error while running CLI for step `{args.step}`")


if __name__ == '__main__':
    run()
