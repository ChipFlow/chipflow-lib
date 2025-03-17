import importlib.metadata
import jsonschema
import os
import sys
import tomli

__version__ = importlib.metadata.version("chipflow_lib")


class ChipFlowError(Exception):
    pass


def _get_cls_by_reference(reference, context):
    module_ref, _, class_ref = reference.partition(":")
    try:
        module_obj = importlib.import_module(module_ref)
    except ModuleNotFoundError as e:
        raise ChipFlowError(f"Module `{module_ref}` referenced by {context} is not found") from e
    try:
        return getattr(module_obj, class_ref)
    except AttributeError as e:
        raise ChipFlowError(f"Module `{module_ref}` referenced by {context} does not define "
                          f"`{class_ref}`") from e


def _ensure_chipflow_root():
    if "CHIPFLOW_ROOT" not in os.environ:
        os.environ["CHIPFLOW_ROOT"] = os.getcwd()
    if os.environ["CHIPFLOW_ROOT"] not in sys.path:
        sys.path.append(os.environ["CHIPFLOW_ROOT"])
    return os.environ["CHIPFLOW_ROOT"]


# TODO: convert to pydantic, one truth of source for the schema
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
            "additionalProperties": False,
            "properties": {
                "project_name": {
                    "type": "string",
                },
                "top": {
                    "type": "object",
                },
                "steps": {
                    "type": "object",
                },
                "clocks": {
                    "type": "object",
                    "patternPropertues": {
                        ".+": {"type": "string"}
                    },
                },
                "resets": {
                    "type": "object",
                    "patternPropertues": {
                        ".+": {"type": "string"}
                    },
                },
                "silicon": {
                    "type": "object",
                    "required": [
                        "process",
                        "package",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "process": {
                            "type": "string",
                            "enum": ["sky130", "gf180", "customer1", "gf130bcd", "ihp_sg13g2"]
                        },
                        "package": {
                            "enum": ["caravel", "cf20", "pga144"]
                        },
                        "pads": {"$ref": "#/$defs/pin"},
                        "power": {"$ref": "#/$defs/pin"},
                        "debug": {
                            "type": "object",
                            "properties": {
                                "heartbeat": {"type": "boolean"}
                            }
                        }
                    },
                },
            },
        },
    },
    "$defs": {
        "pin": {
            "type": "object",
            "additionalProperties": False,
            "minProperties": 1,
            "patternProperties": {
                ".+": {
                    "type": "object",
                    "required": [
                        "type",
                        "loc",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "type": {
                            "enum": ["io", "i", "o", "oe", "clock", "reset", "power", "ground"]
                        },
                        "loc": {
                            "type": "string",
                            "pattern": "^[NSWE]?[0-9]+$"
                        },
                    }
                }
            }
        }
    }
}


def _parse_config():
    chipflow_root = _ensure_chipflow_root()
    config_file = f"{chipflow_root}/chipflow.toml"
    return _parse_config_file(config_file)


def _parse_config_file(config_file):
    with open(config_file, "rb") as f:
        config_dict = tomli.load(f)

    try:
        jsonschema.validate(config_dict, config_schema)
        return config_dict
    except jsonschema.ValidationError as e:
        raise ChipFlowError(f"Syntax error in `chipflow.toml` at `{'.'.join(e.path)}`: {e.message}")
