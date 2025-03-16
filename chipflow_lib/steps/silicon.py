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
from pprint import pprint
from amaranth import *
from amaranth.lib.wiring import connect, flipped

from .. import ChipFlowError
from ..platforms import SiliconPlatform, top_interfaces
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


class SiliconTop(Elaboratable):
    def __init__(self, config={}):
        self._config = config

    def elaborate(self, platform: SiliconPlatform):
        m = Module()

        platform.instantiate_ports(m)

        # heartbeat led (to confirm clock/reset alive)
        if ("debug" in self._config["chipflow"]["silicon"] and
           self._config["chipflow"]["silicon"]["debug"]["heartbeat"]):
            heartbeat_ctr = Signal(23)
            m.d.sync += heartbeat_ctr.eq(heartbeat_ctr + 1)
            m.d.comb += platform.request("heartbeat").o.eq(heartbeat_ctr[-1])

        top, interfaces = top_interfaces(self._config)
        logger.debug(f"SiliconTop top = {top}, interfaces={interfaces}")

        for n, t in top.items():
            setattr(m.submodules, n, t)

        for component, iface in platform.pinlock.port_map.items():
            for iface_name, member, in iface.items():
                for name, port in member.items():
                    platform.ports[port.port_name].wire(
                            m,
                            getattr(getattr(top[component], iface_name), name)
                            )
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
            dotenv.load_dotenv(dotenv_path=dotenv.find_dotenv(usecwd=True))
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
        git_head = subprocess.check_output(
            ["git", "-C", os.environ["CHIPFLOW_ROOT"],
             "rev-parse", "--short", "HEAD"],
            encoding="ascii").rstrip()
        git_dirty = bool(subprocess.check_output(
            ["git", "-C", os.environ["CHIPFLOW_ROOT"],
             "status", "--porcelain", "--untracked-files=no"]))
        submission_name = git_head
        if git_dirty:
            logging.warning("Git tree is dirty, submitting anyway!")
            submission_name += f"-dirty"
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
            logger.debug(f"iface={iface}, port={port}, dir={port.direction}, width={width}")
            if width > 1:
                for i in range(width):
                    padname = f"{iface}{i}"
                    logger.debug(f"padname={padname}, port={port}, loc={port.pins[i]}, "
                                 f"dir={port.direction}, width={width}")
                    pads[padname] = {'loc': port.pins[i], 'type': port.direction.value}
            else:
                padname = f"{iface}"

                logger.debug(f"padname={padname}, port={port}, loc={port.pins[0]}, "
                             f"dir={port.direction}, width={width}")
                pads[padname] = {'loc': port.pins[0], 'type': port.direction.value}
 
        config = {
            "dependency_versions": dep_versions,
            "silicon": {
                "process": self.silicon_config["processes"][0],
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
        endpoint = os.environ.get("CHIPFLOW_API_ENDPOINT", "https://build.chipflow.org/api/builds")
        host = urlparse(endpoint).netloc

        resp = requests.post(
            os.environ.get("CHIPFLOW_API_ENDPOINT", "https://build.chipflow.org/api/builds"),
            auth=(os.environ["CHIPFLOW_API_KEY_ID"], os.environ["CHIPFLOW_API_KEY_SECRET"]),
            data=data,
            files={
                "rtlil": open(rtlil_path, "rb"),
                "config": json.dumps(config),
            })
        
        # Parse response body
        try:
            resp_data = resp.json()
        except ValueError:
            resp_data = resp.text
        
        # Handle response based on status code
        if resp.status_code == 200:
            logger.info(f"Submitted design: {resp_data}")
            print(f"https://{host}/build/{resp_data["build_id"]}")
            
        else:
            # Log detailed information about the failed request
            logger.error(f"Request failed with status code {resp.status_code}")
            logger.error(f"Request URL: {resp.request.url}")
            
            # Log headers with auth information redacted
            headers = dict(resp.request.headers)
            if "Authorization" in headers:
                headers["Authorization"] = "REDACTED"
            logger.error(f"Request headers: {headers}")
            
            logger.error(f"Request data: {data}")
            logger.error(f"Response headers: {dict(resp.headers)}")
            logger.error(f"Response body: {resp_data}")
            
            raise ChipFlowError(f"Failed to submit design: {resp_data}")
