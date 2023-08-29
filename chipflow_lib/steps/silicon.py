# SPDX-License-Identifier: BSD-2-Clause

import os
import sys
import time
import json
import pprint
import inspect
import argparse
import subprocess
import importlib.metadata

import requests

from .. import ChipFlowError
from ..platforms.silicon import SiliconPlatform


class SiliconStep:
    """Prepare and submit the design for an ASIC."""

    def __init__(self, config):
        self.project_id = config["chipflow"].get("project_id")
        self.silicon_config = config["chipflow"]["silicon"]
        self.platform = SiliconPlatform(pads=self.silicon_config["pads"])

    def build_cli_parser(self, parser):
        action_argument = parser.add_subparsers(dest="action")
        prepare_subparser = action_argument.add_parser(
            "prepare", help=inspect.getdoc(self.prepare).splitlines()[0])
        submit_subparser = action_argument.add_parser(
            "submit", help=inspect.getdoc(self.submit).splitlines()[0])
        submit_subparser.add_argument(
            "--dry-run", help=argparse.SUPPRESS,
            default=False, action="store_true")

    def run_cli(self, args):
        if args.action == "submit" and not args.dry_run:
            if self.project_id is None:
                raise ChipFlowError(
                    "Key `chipflow.project_id` is not defined in chipflow.toml; "
                    "see https://chipflow.io/beta for details on how to join the beta")
            if ("CHIPFLOW_API_KEY_ID" not in os.environ or
                    "CHIPFLOW_API_KEY_SECRET" not in os.environ):
                raise ChipFlowError(
                    "Environment variables `CHIPFLOW_API_KEY_ID` and `CHIPFLOW_API_KEY_SECRET` "
                    "must be set in order to submit a design")

        rtlil_path = self.prepare()  # always prepare before submission
        if args.action == "submit":
            self.submit(rtlil_path, dry_run=args.dry_run)

    def prepare(self):
        """Elaborate the design and convert it to RTLIL.

        Returns the path to the RTLIL file.
        """
        raise NotImplementedError

    def submit(self, rtlil_path, *, dry_run=False):
        """Submit the design to the ChipFlow cloud builder.
        """
        git_head = subprocess.check_output(
            ["git", "-C", os.environ["CHIPFLOW_ROOT"],
             "rev-parse", "HEAD"],
            encoding="ascii").rstrip()
        git_dirty = bool(subprocess.check_output(
            ["git", "-C", os.environ["CHIPFLOW_ROOT"],
             "status", "--porcelain", "--untracked-files=no"]))
        submission_name = git_head
        if git_dirty:
            submission_name += f"-dirty.{time.strftime('%Y%m%d%M%H%S', time.gmtime())}"

        dep_versions = {
            "python": sys.version.split()[0]
        }
        for package in (
            # Upstream packages
            "poetry",
            "yowasp-runtime", "yowasp-yosys",
            "amaranth", "amaranth-stdio", "amaranth-soc",
            # ChipFlow packages
            "chipflow-lib",
            "amaranth-orchard", "amaranth-vexriscv",
        ):
            try:
                dep_versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                dep_versions[package] = None
        data = {
            "projectId": self.project_id,
            "name": submission_name,
        }
        config = {
            "dependency_versions": dep_versions,
            "silicon": {
                "process": self.silicon_config["process"],
                "pad_ring": self.silicon_config["pad_ring"],
                "pads": {
                    pad_name: self.silicon_config["pads"][pad_name]
                    for pad_name in self.platform._pins
                },
                "power": self.silicon_config.get("power", {})
            }
        }
        if dry_run:
            print(f"data=\n{json.dumps(data, indent=2)}")
            print(f"files['config']=\n{json.dumps(config, indent=2)}")
            return

        resp = requests.post(
            os.environ.get("CHIPFLOW_API_ENDPOINT", "https://app.chipflow-infra.com/api/builds"),
            auth=(os.environ["CHIPFLOW_API_KEY_ID"], os.environ["CHIPFLOW_API_KEY_SECRET"]),
            data=data,
            files={
                "rtlil": open(rtlil_path, "rb"),
                "config": json.dumps(config),
            })
        resp_data = resp.json()
        if resp.status_code == 403:
            raise ChipFlowError(
                "Authentication failed; please verify the values of the the CHIPFLOW_API_KEY_ID "
                "and CHIPFLOW_API_KEY_SECRET environment variables, if the issue persists, "
                "contact support to resolve it")
        elif resp.status_code >= 400:
            raise ChipFlowError(
                f"Submission failed ({resp_data['statusCode']} {resp_data['error']}: "
                f"{resp_data['message']}); please contact support and provide this error message")
        elif resp.status_code >= 300:
            assert False, "3xx responses should not be returned"
        elif resp.status_code >= 200:
            if not resp_data["ok"]:
                raise ChipFlowError(
                    f"Submission failed ({resp_data['msg']}); please contact support and provide "
                    f"this error message")
            else:
                print(f"{resp_data['msg']} (#{resp_data['id']}: {resp_data['name']}); "
                      f"{resp_data['url']}")
