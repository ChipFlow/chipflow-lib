# SPDX-License-Identifier: BSD-2-Clause

import sys
import argparse
import os
import tomli
import importlib


class ChipFlowError(Exception):
    pass


class Main():
    def _build_arg_parser(self):
        parser = argparse.ArgumentParser()

        parser_action = parser.add_subparsers(dest="action", required=True)
        sim_action = parser_action.add_parser(
            "sim",
            help="Simulate the design.")
        board_action = parser_action.add_parser(
            "board",
            help="Build the design for a board.")
        silicon_action = parser_action.add_parser(
            "silicon",
            help="Build the design for an ASIC.")
        software_action = parser_action.add_parser(
            "software",
            help="Build the software.")

        return parser

    def _parse_config(self, args):
        config_dir = os.getcwd()
        config_file = f"{config_dir}/chipflow.toml"

        # TODO: Add better validation/errors for loading chipflow.toml
        with open(config_file, mode="rb") as fp:
            self.config = tomli.load(fp)

    def run(self):
        # FIXME: temporary hack for sim_platform.SimPlatform.__init__
        os.environ["BUILD_DIR"] = "./build/sim"

        parser = self._build_arg_parser()

        args = parser.parse_args()

        self._parse_config(args)

        getattr(self, 'run_' + args.action)(args)

    def _get_context(self, name):
        reference = self.config["chipflow"][name]
        module_ref, _, class_ref = reference.partition(":")
        try:
            cls = getattr(importlib.import_module(module_ref), class_ref)
        except ModuleNotFoundError as e:
            raise NameError(f"Module {module_ref} referenced by context `{name}` is not found")
        except AttributeError as e:
            raise NameError(f"Module {module_ref} referenced by context `{name}` does not define "
                            f"`{class_ref}`")
        return cls(self.config)

    def run_sim(self, args):
        self._get_context("sim_context").build()

    def run_board(self, args):
        self._get_context("board_context").build()

    def run_silicon(self, args):
        self._get_context("silicon_context").build()

    def run_software(self, args):
        self._get_context("software_context").build()


if __name__ == '__main__':
    Main().run()
