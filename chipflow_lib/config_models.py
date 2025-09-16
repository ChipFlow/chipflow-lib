# SPDX-License-Identifier: BSD-2-Clause
from enum import Enum
from typing import Dict, Optional, Any, List, Annotated

from pydantic import (
        BaseModel, PlainSerializer, WrapValidator
        )

from ._appresponse import AppResponseModel, OmitIfNone

class Process(Enum):
    """
    IC manufacturing process
    """
    #: Skywater foundry open-source 130nm process
    SKY130 = "sky130"
    #: GlobalFoundries open-source 130nm process
    GF180 = "gf180"
    #: Pragmatic Semiconductor FlexIC process (old)
    HELVELLYN2 = "helvellyn2"
    #: GlobalFoundries 130nm BCD process
    GF130BCD = "gf130bcd"
    #: IHP open source 130nm SiGe Bi-CMOS process
    IHP_SG13G2 = "ihp_sg13g2"

    def __str__(self):
        return f'{self.value}'



Voltage = Annotated[
              float,
              PlainSerializer(lambda x: f'{x:.1e}V', return_type=str),
              WrapValidator(lambda v, h: h(v.strip('Vv ') if isinstance(v, str) else h(v)))
          ]


class VoltageRange(AppResponseModel):
    """
    Models a voltage range for a power domain or IO
    """
    min: Annotated[Optional[Voltage], OmitIfNone()] = None
    max: Annotated[Optional[Voltage], OmitIfNone()] = None
    typical: Annotated[Optional[Voltage], OmitIfNone()] = None


class SiliconConfig(BaseModel):
    """Configuration for silicon in chipflow.toml."""
    process: 'Process'
    package: str
    power: Dict[str, Voltage] = {}
    debug: Optional[Dict[str, bool]] = None
    # This is still kept around to allow forcing pad locations.

class SimulationConfig(BaseModel):
    num_steps: int = 3000000

class CompilerConfig(BaseModel):
    cpu: str
    abi: str

class SoftwareConfig(BaseModel):
    riscv: CompilerConfig = CompilerConfig(cpu="baseline_rv32-a-c-d", abi="ilp32")

class ChipFlowConfig(BaseModel):
    """Root configuration for chipflow.toml."""
    project_name: str
    top: Dict[str, Any] = {}
    steps: Optional[Dict[str, str]] = None
    silicon: Optional[SiliconConfig] = None
    simulation: SimulationConfig = SimulationConfig()
    software: SoftwareConfig = SoftwareConfig()
    clock_domains: Optional[List[str]] = None


class Config(BaseModel):
    """Root configuration model for chipflow.toml."""
    chipflow: ChipFlowConfig
