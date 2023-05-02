# SPDX-License-Identifier: BSD-2-Clause

class BoardStep:
    """Build the design for a board."""

    def __init__(self, config, platform):
        self.platform = platform

    def build_cli_parser(self, parser):
        pass

    def run_cli(self, args):
        self.build()

    def build(self):
        self.platform.build()
