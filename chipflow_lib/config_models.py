# SPDX-License-Identifier: BSD-2-Clause
import re
from typing import Dict, Optional, Literal, Any

from pydantic import BaseModel, model_validator, ValidationInfo, field_validator

from .platforms.utils import Process


class PadConfig(BaseModel):
    """Configuration for a pad in chipflow.toml."""
    type: Literal["io", "i", "o", "oe", "clock", "reset", "power", "ground"]
    loc: str

    @model_validator(mode="after")
    def validate_loc_format(self):
        """Validate that the location is in the correct format."""
        if not re.match(r"^[NSWE]?[0-9]+$", self.loc):
            raise ValueError(f"Invalid location format: {self.loc}, expected format: [NSWE]?[0-9]+")
        return self

    @classmethod
    def validate_pad_dict(cls, v: dict, info: ValidationInfo):
        """Custom validation for pad dicts from TOML that may not have all fields."""
        if isinstance(v, dict):
            # Handle legacy format - if 'type' is missing but should be inferred from context
            if 'loc' in v and 'type' not in v:
                if info.field_name == 'power':
                    v['type'] = 'power'

            # Map legacy 'clk' type to 'clock' to match our enum
            if 'type' in v and v['type'] == 'clk':
                v['type'] = 'clock'

            return v
        return v


class SiliconConfig(BaseModel):
    """Configuration for silicon in chipflow.toml."""
    process: Process
    package: Literal["caravel", "cf20", "pga144"]
    pads: Dict[str, PadConfig] = {}
    power: Dict[str, PadConfig] = {}
    debug: Optional[Dict[str, bool]] = None

    @field_validator('pads', 'power', mode='before')
    @classmethod
    def validate_pad_dicts(cls, v, info: ValidationInfo):
        """Pre-process pad dictionaries to handle legacy format."""
        if isinstance(v, dict):
            result = {}
            for key, pad_dict in v.items():
                # Apply the pad validator with context about which field we're in
                validated_pad = PadConfig.validate_pad_dict(pad_dict, info)
                result[key] = validated_pad
            return result
        return v


class BoardType(BaseModel):
    """Configuration for silicon in chipflow.toml."""
    board_name: Literal["ULX3S"]
    board_type: Literal["85F"]



class StepsConfig(BaseModel):
    """Configuration for steps in chipflow.toml."""
    silicon: str


class ChipFlowConfig(BaseModel):
    """Root configuration for chipflow.toml."""
    project_name: Optional[str] = None
    top: Dict[str, Any] = {}
    steps: StepsConfig
    silicon: SiliconConfig
    board: BoardConfig
    clocks: Optional[Dict[str, str]] = None
    resets: Optional[Dict[str, str]] = None


class Config(BaseModel):
    """Root configuration model for chipflow.toml."""
    chipflow: ChipFlowConfig
