"""
Chipflow library
"""

import importlib.metadata
import logging
import os
import sys
import tomli
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config_models import Config

__version__ = importlib.metadata.version("chipflow_lib")


logger = logging.getLogger(__name__)

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
    root = getattr(_ensure_chipflow_root, 'root', None)
    if root:
        return root

    if "CHIPFLOW_ROOT" not in os.environ:
        logger.debug(f"CHIPFLOW_ROOT not found in environment. Setting CHIPFLOW_ROOT to {os.getcwd()} for any child scripts")
        os.environ["CHIPFLOW_ROOT"] = os.getcwd()
    else:
        logger.debug(f"CHIPFLOW_ROOT={os.environ['CHIPFLOW_ROOT']} found in environment")

    if os.environ["CHIPFLOW_ROOT"] not in sys.path:
        sys.path.append(os.environ["CHIPFLOW_ROOT"])
    _ensure_chipflow_root.root = Path(os.environ["CHIPFLOW_ROOT"]).absolute()  #type: ignore
    return _ensure_chipflow_root.root  #type: ignore


def _get_src_loc(src_loc_at=0):
      frame = sys._getframe(1 + src_loc_at)
      return (frame.f_code.co_filename, frame.f_lineno)



def _parse_config() -> 'Config':
    """Parse the chipflow.toml configuration file."""
    from .config import _parse_config_file
    chipflow_root = _ensure_chipflow_root()
    config_file = Path(chipflow_root) / "chipflow.toml"
    try:
        return _parse_config_file(config_file)
    except FileNotFoundError:
       raise ChipFlowError(f"Config file not found. I expected to find it at {config_file}")
    except tomli.TOMLDecodeError as e:
        raise ChipFlowError(f"TOML Error found when loading {config_file}: {e.msg} at line {e.lineno}, column {e.colno}")
