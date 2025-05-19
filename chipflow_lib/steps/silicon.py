# SPDX-License-Identifier: BSD-2-Clause

import argparse
import inspect
import json
import logging
import os
import requests
import subprocess
import time
import sys

import dotenv
from amaranth import *

from . import StepBase
from .. import ChipFlowError
from ..platforms import SiliconPlatform, top_interfaces, load_pinlock
from ..platforms.utils import PinSignature


logger = logging.getLogger(__name__)


class SiliconTop(StepBase, Elaboratable):
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
                    iface = getattr(top[component], iface_name)
                    wire = (iface if isinstance(iface.signature, PinSignature)
                            else getattr(iface, name))
                    platform.ports[port.port_name].wire(m, wire)
        return m


class SiliconStep:
    """Step to Prepare and submit the design for an ASIC."""
    def __init__(self, config):
        self.config = config

        # Also parse with Pydantic for type checking and better code structure
        from chipflow_lib.config_models import Config
        self.config_model = Config.model_validate(config)
        self.project_name = self.config_model.chipflow.project_name
        self.silicon_config = config["chipflow"]["silicon"]  # Keep for backward compatibility
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
        submit_subparser.add_argument(
            "--wait", help=argparse.SUPPRESS,
            default=False, action="store_true")

    def run_cli(self, args):
        if args.action == "submit" and not args.dry_run:
            dotenv.load_dotenv(dotenv_path=dotenv.find_dotenv(usecwd=True))
            if self.project_name is None:
                raise ChipFlowError(
                    "Key `chipflow.project_id` is not defined in chipflow.toml; "
                    "see https://chipflow.io/beta for details on how to join the beta")

        rtlil_path = self.prepare()  # always prepare before submission
        if args.action == "submit":
            self.submit(rtlil_path, dry_run=args.dry_run, wait=args.wait)

    def prepare(self):
        """Elaborate the design and convert it to RTLIL.

        Returns the path to the RTLIL file.
        """
        return self.platform.build(SiliconTop(self.config), name=self.config_model.chipflow.project_name)

    def submit(self, rtlil_path, *, dry_run=False, wait=False):
        """Submit the design to the ChipFlow cloud builder.
        """
        if not dry_run:
            # Check for CHIPFLOW_API_KEY_SECRET or CHIPFLOW_API_KEY
            if not os.environ.get("CHIPFLOW_API_KEY") and not os.environ.get("CHIPFLOW_API_KEY_SECRET"):
                raise ChipFlowError(
                    "Environment variable `CHIPFLOW_API_KEY` must be set to submit a design."
                )
            # Log a deprecation warning if CHIPFLOW_API_KEY_SECRET is used
            if os.environ.get("CHIPFLOW_API_KEY_SECRET"):
                logger.warning(
                    "Environment variable `CHIPFLOW_API_KEY_SECRET` is deprecated. "
                    "Please migrate to using `CHIPFLOW_API_KEY` instead."
                )
            chipflow_api_key = os.environ.get("CHIPFLOW_API_KEY") or os.environ.get("CHIPFLOW_API_KEY_SECRET")
            if chipflow_api_key is None:
                raise ChipFlowError(
                    "Environment variable `CHIPFLOW_API_KEY` is empty."
                )

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
            submission_name += "-dirty"

        data = {
            "projectId": self.project_name,
            "name": submission_name,
        }

        # Dev only var to select specifc backend version
        # Check if CHIPFLOW_BACKEND_VERSION exists in the environment and add it to the data dictionary
        chipflow_backend_version = os.environ.get("CHIPFLOW_BACKEND_VERSION")
        if chipflow_backend_version:
            data["chipflow_backend_version"] = chipflow_backend_version

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

        pinlock = load_pinlock()
        config = pinlock.model_dump_json(indent=2)

        if dry_run:
            print(f"data=\n{json.dumps(data, indent=2)}")
            print(f"files['config']=\n{config}")
            return

        logger.info(f"Submitting {submission_name} for project {self.project_name}")
        chipflow_api_origin = os.environ.get("CHIPFLOW_API_ORIGIN", "https://build.chipflow.org")
        build_submit_url = f"{chipflow_api_origin}/build/submit"

        resp = requests.post(
            build_submit_url,
            # TODO: This needs to be reworked to accept only one key, auth accepts user and pass
            # TODO: but we want to submit a single key
            auth=(None, chipflow_api_key),
            data=data,
            files={
                "rtlil": open(rtlil_path, "rb"),
                "config": config,
            },
            allow_redirects=False
            )

        # Parse response body
        try:
            resp_data = resp.json()
        except ValueError:
            resp_data = resp.text

        # Handle response based on status code
        if resp.status_code == 200:
            logger.info(f"Submitted design: {resp_data}")
            build_url = f"{chipflow_api_origin}/build/{resp_data['build_id']}"
            build_status_url = f"{chipflow_api_origin}/build/{resp_data['build_id']}/status"
            log_stream_url = f"{chipflow_api_origin}/build/{resp_data['build_id']}/logs?follow=true"

            print(f"Design submitted successfully! Build URL: {build_url}")

            # Poll the status API until the build is completed or failed
            stream_event_counter = 0
            fail_counter = 0
            warned_last = False
            timeout = 10.0;

            if wait:
                while True:
                    logger.info("Polling build status...")
                    try:
                        status_resp = requests.get(
                            build_status_url,
                            auth=(None, chipflow_api_key),
                            timeout=timeout
                        )
                        if status_resp.status_code != 200:
                            fail_counter += 1
                            logger.error(f"Failed to fetch build status {fail_counter} times: {status_resp.text}")
                            if fail_counter > 5:
                                logger.error(f"Failed to fetch build status {fail_counter} times. Exiting.")
                                raise ChipFlowError("Error while checking build status.")
                    except requests.Timeout:
                        continue  #go round again

                    status_data = status_resp.json()
                    build_status = status_data.get("status")
                    logger.info(f"Build status: {build_status}")

                    if build_status == "completed":
                        print("Build completed successfully!")
                        exit(0)
                    elif build_status == "failed":
                        print("Build failed.")
                        exit(1)
                    elif build_status == "running":
                        print("Build running.")
                        # Wait before polling again
                        # time.sleep(10)
                        # Attempt to stream logs rather than time.sleep
                        try:
                            if stream_event_counter > 1 and not warned_last:
                                logger.warning("Log streaming may have been interrupted. Some logs may be missing.")
                                logger.warning(f"Check {build_url}")
                                warned_last = True
                            with requests.get(
                                log_stream_url,
                                auth=(None, chipflow_api_key),
                                stream=True, timeout=timeout
                            ) as log_resp:
                                if log_resp.status_code == 200:
                                    warned_last = False
                                    for line in log_resp.iter_lines():
                                        if line:
                                            print(line.decode("utf-8"))  # Print logs in real-time
                                            sys.stdout.flush()
                                else:
                                    logger.warning(f"Failed to stream logs: {log_resp.text}")
                                    stream_event_counter += 1
                        except requests.Timeout as e:
                            continue  #go round again
                        except requests.RequestException as e:
                            logger.error(f"Error while streaming logs: {e}")
                            stream_event_counter += 1
                            pass
                    time.sleep(0.5)  # Wait before polling again
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
