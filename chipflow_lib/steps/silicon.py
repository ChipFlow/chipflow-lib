# SPDX-License-Identifier: BSD-2-Clause

import argparse
import importlib.metadata
import inspect
import json
import logging
import os
import requests
import subprocess
import sys
import time

import dotenv

from amaranth import *

from .. import ChipFlowError
from ..platforms import SiliconPlatform, top_interfaces


logger = logging.getLogger(__name__)


class SiliconTop(Elaboratable):
    def __init__(self, config={}):
        self._config = config

    def elaborate(self, platform: SiliconPlatform):
        m = Module()

        platform.instantiate_ports(m)

        # heartbeat led (to confirm clock/reset alive)
        if ("config" in self._config["chipflow"]["silicon"] and
           self._config["chipflow"]["silicon"]["debug"]["heartbeat"]):
            heartbeat_ctr = Signal(23)
            m.d.sync += heartbeat_ctr.eq(heartbeat_ctr + 1)
            m.d.comb += platform.request("heartbeat").o.eq(heartbeat_ctr[-1])

        top, interfaces = top_interfaces(self._config)
        for n, t in top.items():
            setattr(m.submodules, n, t)

        return m


class SiliconStep:
    """Prepare and submit the design for an ASIC."""
    def __init__(self, config):
        self.config = config
        self.project_name = config["chipflow"].get("project_name")
        self.silicon_config = config["chipflow"]["silicon"]
        self.platform = SiliconPlatform(config)

    def build_cli_parser(self, parser):
        action_argument = parser.add_subparsers(dest="action")
        action_argument.add_parser(
            "prepare", help=inspect.getdoc(self.prepare).splitlines()[0])
        submit_subparser = action_argument.add_parser(
            "submit", help=inspect.getdoc(self.submit).splitlines()[0])
        submit_subparser.add_argument(
            "--dry-run", help=argparse.SUPPRESS,
            default=False, action="store_true")

    def run_cli(self, args):
        if args.action == "submit" and not args.dry_run:
            if self.project_name is None:
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
        return self.platform.build(SiliconTop(self.config), name=self.config["chipflow"]["project_name"])

    def submit(self, rtlil_path, *, dry_run=False):
        """Submit the design to the ChipFlow cloud builder.
        """
        dotenv.load_dotenv()
        git_head = subprocess.check_output(
            ["git", "-C", os.environ["CHIPFLOW_ROOT"],
             "rev-parse", "HEAD"],
            encoding="ascii").rstrip()
        git_dirty = bool(subprocess.check_output(
            ["git", "-C", os.environ["CHIPFLOW_ROOT"],
             "status", "--porcelain", "--untracked-files=no"]))
        submission_name = git_head
        if git_dirty:
            logging.warning("Git tree is dirty, submitting anyway!")
            submission_name += f"-dirty.{time.strftime('%Y%m%d%M%H%S', time.gmtime())}"
        dep_versions = {
            "python": sys.version.split()[0]
        }
        for package in (
            # Upstream packages
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
            "projectId": self.project_name,
            "name": submission_name,
        }

        pads = {}
        for iface, port in self.platform._ports.items():
            width = len(port.pins)
            print(f"iface={iface}, port={port}, dir={port.direction}, width={width}")
            if width > 1:
                for i in range(width):
                    padname = f"{iface}{i}"
                    print(f"padname={padname}, port={port}, loc={port.pins[i:i+1]}, "
                          f"dir={port.direction}, width={width}")
                    pads[padname] = {'loc': port.pins[i:i+1], 'dir': port.direction}

        config = {
            "dependency_versions": dep_versions,
            "silicon": {
                "process": self.silicon_config["process"],
                "pad_ring": self.silicon_config["package"],
                "pads": pads,
                "power": self.silicon_config.get("power", {})
            }
        }
        if dry_run:
            print(f"data=\n{json.dumps(data, indent=2)}")
            print(f"files['config']=\n{json.dumps(config, indent=2)}")
            return

        logger.info(f"Submitting {submission_name} for project {self.project_name}")

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
        else:
            ChipFlowError(f"Unexpected response from API: {resp}")
