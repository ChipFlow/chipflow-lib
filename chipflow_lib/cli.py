# SPDX-License-Identifier: BSD-2-Clause
import sys
import argparse
import os
import tomli
import importlib
from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain


class ChipFlowError(Exception):
    pass


class Main():
    def _build_arg_parser(self):
        parser = argparse.ArgumentParser()

        parser_action = parser.add_subparsers(dest="action", required=True)

        # Simulation
        sim_action = parser_action.add_parser("sim", help="Simulate the design.")
        sim_subparser = sim_action.add_subparsers(dest="sim_action")
        sim_subparser.add_parser("build", help="Build the simulation binary.")
        sim_subparser.add_parser("build-yosys", help="Build the intermediate Yosys simulation.")

        # Board
        board_action = parser_action.add_parser("board", help="Build the design for a board.")

        # Silicon
        silicon_action = parser_action.add_parser("silicon", help="Build the design for an ASIC.")

        # Software/BIOS
        software_action = parser_action.add_parser("software", help="Build the software.")

        return parser

    def _parse_config(self, args):
        config_dir = os.getcwd()
        config_file = f"{config_dir}/chipflow.toml"

        # TODO: Add better validation/errors for loading chipflow.toml
        with open(config_file, mode="rb") as fp:
            self.config = tomli.load(fp)

    def run(self):
        parser = self._build_arg_parser()

        args = parser.parse_args()

        self._parse_config(args)

        getattr(self, 'run_' + args.action)(args)

    def _load(self, loader_name):
        try:
            module_loc = self.config["chipflow"]["loader_module"]

            module = importlib.import_module(module_loc)
        except ModuleNotFoundError as error:
            raise ChipFlowError("Could not locate module, {module_loc}.") from error

        if (not hasattr(module, loader_name)):
            raise ChipFlowError(f"Loader module is missing loader. module={module_loc}, loader={loader_name}")

        return getattr(module, loader_name)(self.config)

    def _load_module(self, module_loc):
        try:
            module = importlib.import_module(module_loc)
        except ModuleNotFoundError as error:
            raise ChipFlowError("Could not load module, {module_loc}.") from error

        return module

    def _load_design_module(self):
        return self._load_module(self.config["chipflow"]["design_module"])

    def _sim_build_yosys(self):
        context = self._load("load_sim_context")
        context.build()

    def run_sim(self, args):
        if args.sim_action in (None, "build"):
            module_loc = self.config["chipflow"]["sim_module"]
            doit_build_module = self._load_module(module_loc + ".doit_build")

            cmd = ["build_sim"]
            DoitMain(ModuleTaskLoader(doit_build_module)).run(cmd)

        elif args.sim_action == "build-yosys":
            return self._sim_build_yosys()

        else:
            assert False

    def run_board(self, args):
        context = self._load("load_board_context")
        context.build()

    def run_silicon(self, args):
        context = self._load("load_silicon_context")
        context.build()

    def run_software(self, args):
        module_loc = self.config["chipflow"]["software_module"]
        doit_build_module = self._load_module(module_loc + ".doit_build")

        cmd = ["build_software"]
        DoitMain(ModuleTaskLoader(doit_build_module)).run(cmd)


if __name__ == '__main__':
    Main().run()