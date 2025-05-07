# SPDX-License-Identifier: BSD-2-Clause

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain

from . import StepBase

class SoftwareStep(StepBase):
    """Base step to build the software."""

    doit_build_module = None

    def __init__(self, config):
        pass

    def build_cli_parser(self, parser):
        pass

    def run_cli(self, args):
        self.build()

    def doit_build(self):
        "Run the overridden doit_build_module"
        DoitMain(ModuleTaskLoader(self.doit_build_module)).run(["build_software"])

    def build(self):
        "Build the software for your design"
        self.doit_build()
