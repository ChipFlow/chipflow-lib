# SPDX-License-Identifier: BSD-2-Clause

import os
import time
import json
import inspect
import subprocess

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
        action_argument.add_parser(
            "prepare", help=inspect.getdoc(self.prepare).splitlines()[0])
        action_argument.add_parser(
            "submit", help=inspect.getdoc(self.submit).splitlines()[0])

    def run_cli(self, args):
        if args.action == "submit":
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
            self.submit(rtlil_path)

    def prepare(self):
        """Elaborate the design and convert it to RTLIL.

        Returns the path to the RTLIL file.
        """
        raise NotImplementedError

    def submit(self, rtlil_path):
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

        resp = requests.post(
            os.environ.get("CHIPFLOW_API_ENDPOINT", "https://app.chipflow-infra.com/api/builds"),
            auth=(os.environ["CHIPFLOW_API_KEY_ID"], os.environ["CHIPFLOW_API_KEY_SECRET"]),
            data={
                "projectId": self.project_id,
                "name": submission_name,
            },
            files={
                "rtlil": open(rtlil_path, "rb"),
                "config": json.dumps({"silicon": self.silicon_config}),
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
                print(f"{resp_data['msg']} (#{resp_data['id']}: {resp_data['name']})")
