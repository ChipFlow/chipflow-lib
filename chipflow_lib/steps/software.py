# SPDX-License-Identifier: BSD-2-Clause

import logging

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain
from amaranth import Module

from . import StepBase
from .. import ChipFlowError
from ..platforms._software import SoftwarePlatform
from ..platforms._utils import top_components

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

    def build(self, *args):
        "Build the software for your design"
        print("Building software...")

        m = Module()
        top = top_components(self._config)
        logger.debug(f"SoftwareStep top = {top}")
        logger.debug("-> Adding top components:")

        for n, t in top.items():
            setattr(m.submodules, n, t)

        generators = self._platform.build(m, top)

        from ..platforms import software_build
        for name, gen in generators.items():
            loader = ModuleTaskLoader(software_build)
            loader.task_opts = {"build_software": {"generator": gen}, "build_software_elf": {'generator': gen}}  #type: ignore
            if DoitMain(loader).run(["build_software"]) != 0:
                raise ChipFlowError("Software Build failed")
