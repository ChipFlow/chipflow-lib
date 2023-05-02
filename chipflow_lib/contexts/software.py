# SPDX-License-Identifier: BSD-2-Clause

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain


class SoftwareContext:
    doit_build_module = None

    def doit_build(self):
        DoitMain(ModuleTaskLoader(self.doit_build_module)).run(["build_software"])

    def build(self):
        self.doit_build()
