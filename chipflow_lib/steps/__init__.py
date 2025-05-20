"""
Steps provide an extensible way to modify the `chipflow` command behavior for a given design
"""

import os
from abc import ABC

def setup_amaranth_tools():
    _amaranth_settings = {
        "AMARANTH_USE_YOSYS": "system",
        "YOSYS": "yowasp-yosys",
        "SBY": "yowasp-sby",
        "SMTBMC": "yowasp-yosys-smtbmc",
        "NEXTPNR_ICE40": "yowasp-nextpnr-ice40",
        "ICEPACK": "yowasp-icepackr",
        "NEXTPNR_ECP5": "yowasp-nextpnr-ecp5",
        "ECPBRAM": "yowasp-ecpbram",
        "ECPMULTI": "yowasp-ecpmulti",
        "ECPPACK": "yowasp-ecppack",
        "ECPPLL": "yowasp-ecppll",
        "ECPUNPACK": "yowasp-ecpunpack",
        "NEXTPNR-ECP5": "yowasp-nextpnr-ecp5",
        "YOSYS-WITNESS": "yowasp-yosys-witness",
    }

    os.environ |= _amaranth_settings

class StepBase(ABC):
    def __init__(self, config={}):
        ...

    def build_cli_parser(self, parser):
        "Build the cli parser for this step"
        ...

    def run_cli(self, args):
        "Called when this step's is used from `chipflow` command"
        self.build()
