# SPDX-License-Identifier: BSD-2-Clause
from typing import Dict, Optional, Literal, Any, List

from pydantic import BaseModel

from .platforms._utils import Process, PowerConfig

Voltage = float

class SiliconConfig(BaseModel):
    """Configuration for silicon in chipflow.toml."""
    process: 'Process'
    package: Literal["caravel", "cf20", "pga144"]
    power: Dict[str, Voltage] = {}
    debug: Optional[Dict[str, bool]] = None

# TODO: add validation that top components, clock domains and power domains
#       not begin with '_' (unless power domain _core)
class ChipFlowConfig(BaseModel):
    """Root configuration for chipflow.toml."""
    project_name: str
    top: Dict[str, Any] = {}
    steps: Optional[Dict[str, str]] = None
    silicon: Optional[SiliconConfig] = None
    clock_domains: Optional[List[str]] = None
    power: Optional[PowerConfig] = None


class Config(BaseModel):
    """Root configuration model for chipflow.toml."""
    chipflow: ChipFlowConfig
