# SPDX-License-Identifier: BSD-2-Clause

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain


class SoftwareStep:
    """Build the software."""

    doit_build_module = None

    def __init__(self, config):
        pass

    def build_cli_parser(self, parser):
        pass

    def run_cli(self, args):
        self.build()

    def doit_build(self):
        DoitMain(ModuleTaskLoader(self.doit_build_module)).run(["build_software"])

    def build(self):
        self.doit_build()
