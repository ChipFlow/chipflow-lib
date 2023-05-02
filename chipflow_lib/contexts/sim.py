# SPDX-License-Identifier: BSD-2-Clause

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain


class SimContext:
    doit_build_module = None

    def __init__(self, config, platform):
        self.platform = platform

    def doit_build(self):
        DoitMain(ModuleTaskLoader(self.doit_build_module)).run(["build_sim"])

    def build(self):
        self.platform.build()
        self.doit_build()
