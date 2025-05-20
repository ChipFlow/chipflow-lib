# SPDX-License-Identifier: BSD-2-Clause
from . import StepBase, setup_amaranth_tools

class BoardStep(StepBase):
    """Build the design for a board."""

    def __init__(self, config, platform):
        self.platform = platform
        setup_amaranth_tools()

    def build_cli_parser(self, parser):
        pass

    def run_cli(self, args):
        self.build()

    def build(self):
        "Build for the given platform"
        self.platform.build()
