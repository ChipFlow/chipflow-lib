# SPDX-License-Identifier: BSD-2-Clause

import logging

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain
from amaranth import Module

from . import StepBase
from ..platforms._internal import SoftwarePlatform, top_components

logger = logging.getLogger(__name__)

class SoftwareStep(StepBase):
    """Base step to build the software."""

    doit_build_module = None

    def __init__(self, config):
        self._platform = SoftwarePlatform(config)
        self._config = config

    def build_cli_parser(self, parser):
        pass

    def run_cli(self, args):
        self.build()

    def doit_build(self):
        "Run the overridden :doit_build_module"
        DoitMain(ModuleTaskLoader(self.doit_build_module)).run(["build_software"])

    def build(self, *args):
        "Build the software for your design"

        print("building software")

        m = Module()
        top = top_components(self._config)
        logger.debug(f"SoftwareStep top = {top}")
        logger.debug("-> Adding top components:")

        for n, t in top.items():
            setattr(m.submodules, n, t)

        self._platform.build(m, top)

        self.doit_build()
