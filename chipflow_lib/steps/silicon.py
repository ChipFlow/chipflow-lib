# SPDX-License-Identifier: BSD-2-Clause

from ..platforms.silicon import SiliconPlatform


class SiliconStep:
    """Build the design for an ASIC."""

    def __init__(self, config):
        self.platform = SiliconPlatform(pads=config["chipflow"]["silicon"]["pads"])

    def build_cli_parser(self, parser):
        pass

    def run_cli(self, args):
        self.build()

    def build(self):
        self.platform.build()
