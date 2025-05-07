"""
Steps provide an extensible way to modify the `chipflow` command behavior for a given design
"""

from abc import ABC

class StepBase(ABC):
    def __init__(self, config={}):
        ...

    def build_cli_parser(self, parser):
        "Build the cli parser for this step"
        ...

    def run_cli(self, args):
        "Called when this step's is used from `chipflow` command"
        self.build()
