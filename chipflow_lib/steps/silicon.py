# amaranth: UnusedElaboratable=no

# SPDX-License-Identifier: BSD-2-Clause

import argparse
import inspect
import json
import logging
import os
import re
import requests
import shutil
import subprocess
import sys
import time
import urllib3
from pprint import pformat


import dotenv

from amaranth import Module, Signal, Elaboratable
from halo import Halo

from . import StepBase, _wire_up_ports
from .. import ChipFlowError
from ..cli import log_level
from ..platforms._internal import SiliconPlatform, top_components, load_pinlock


logger = logging.getLogger(__name__)


class SiliconTop(StepBase, Elaboratable):
    def __init__(self, config):
        self._config = config

    def elaborate(self, platform: SiliconPlatform):
        m = Module()

        platform.instantiate_ports(m)

        # heartbeat led (to confirm clock/reset alive)
        if (self._config.chipflow.silicon.debug and
           self._config.chipflow.silicon.debug.get('heartbeat', False)):
            heartbeat_ctr = Signal(23)
            m.d.sync += heartbeat_ctr.eq(heartbeat_ctr + 1)
            m.d.comb += platform.request("heartbeat").o.eq(heartbeat_ctr[-1])

        top = top_components(self._config)
        assert platform._pinlock
        logger.debug(f"SiliconTop top = {top}")
        logger.debug(f"port map ports =\n{pformat(platform._pinlock.port_map.ports)}")

        _wire_up_ports(m, top, platform)
        return m


class SiliconStep:
    """Step to Prepare and submit the design for an ASIC."""
    def __init__(self, config):
        self.config = config

        self.platform = SiliconPlatform(config)
        self._log_file = None

    def build_cli_parser(self, parser):
        action_argument = parser.add_subparsers(dest="action")
        action_argument.add_parser(
            "prepare", help=inspect.getdoc(self.prepare).splitlines()[0])   # type: ignore
        submit_subparser = action_argument.add_parser(
            "submit", help=inspect.getdoc(self.submit).splitlines()[0])  # type: ignore
        submit_subparser.add_argument(
            "--dry-run", help=argparse.SUPPRESS,
            default=False, action="store_true")
        submit_subparser.add_argument(
            "--wait", help=argparse.SUPPRESS,
            default=False, action="store_true")

    def run_cli(self, args):
        load_pinlock()  # check pinlock first so we error cleanly
        if args.action == "submit" and not args.dry_run:
            dotenv.load_dotenv(dotenv_path=dotenv.find_dotenv(usecwd=True))

        rtlil_path = self.prepare()  # always prepare before submission
        if args.action == "submit":
            self.submit(rtlil_path, args)

    def prepare(self):
        """Elaborate the design and convert it to RTLIL.

        Returns the path to the RTLIL file.
        """
        return self.platform.build(SiliconTop(self.config), name=self.config.chipflow.project_name)

    def submit(self, rtlil_path, args):
        """Submit the design to the ChipFlow cloud builder.
        Options:
          --dry-run: Don't actually submit
          --wait: Wait until build has completed. Use '-v' to increase level of verbosity
          --log-file <file>: Log full debug output to file
        """
        if not args.dry_run:
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
            self._chipflow_api_key = os.environ.get("CHIPFLOW_API_KEY") or os.environ.get("CHIPFLOW_API_KEY_SECRET")
            if self._chipflow_api_key is None:
                raise ChipFlowError(
                    "Environment variable `CHIPFLOW_API_KEY` is empty."
                )
        if not sys.stdout.isatty():
            interval = 5000  # lets not animate..
        else:
            interval = -1
        with  Halo(text="Submitting...", spinner="dots", interval=interval) as sp:
            fh = None
            submission_name = self.determine_submission_name()
            data = {
                "projectId": self.config.chipflow.project_name,
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
                logger.debug(f"Loading port from pinlock: iface={iface}, port={port}, dir={port.direction}, width={width}")
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

            if args.dry_run:
                sp.succeed(f"✅ Design `{data['projectId']}:{data['name']}` ready for submission to ChipFlow cloud!")
                logger.debug(f"data=\n{json.dumps(data, indent=2)}")
                logger.debug(f"files['config']=\n{config}")
                shutil.copyfile(rtlil_path, 'rtlil')
                with open("data", 'w') as f:
                    json.dump(data, f)
                with open("config", 'w') as f:
                    f.write(config)
                return

            def network_err(e):
                nonlocal fh, sp
                sp.text = ""
                sp.fail("💥 Failed connecting to ChipFlow Cloud due to network error")
                logger.debug(f"Error while getting build status: {e}")
                if fh:
                    fh.close()
                exit(1)

            chipflow_api_origin = os.environ.get("CHIPFLOW_API_ORIGIN", "https://build.chipflow.org")
            build_submit_url = f"{chipflow_api_origin}/build/submit"

            sp.info(f"> Submitting {submission_name} for project {self.config.chipflow.project_name} to ChipFlow Cloud {chipflow_api_origin}")
            sp.start("Sending design to ChipFlow Cloud")

            assert self._chipflow_api_key
            resp = None
            try:
                resp = requests.post(
                    build_submit_url,
                    # TODO: This needs to be reworked to accept only one key, auth accepts user and pass
                    # TODO: but we want to submit a single key
                    auth=("", self._chipflow_api_key),
                    data=data,
                    files={
                        "rtlil": open(rtlil_path, "rb"),
                        "config": config,
                    },
                    allow_redirects=False
                    )
            except requests.ConnectTimeout as e:
               network_err(e)
            except requests.ConnectionError as e:
                if type(e.__context__) is urllib3.exceptions.MaxRetryError:
                    network_err(e)
            except Exception as e:
                network_err(e)

            assert resp
            # Parse response body
            try:
                resp_data = resp.json()
            except ValueError:
                resp_data = {'message': resp.text}

            # Handle response based on status code
            if resp.status_code == 200:
                logger.debug(f"Submitted design: {resp_data}")
                self._build_url = f"{chipflow_api_origin}/build/{resp_data['build_id']}"
                self._build_status_url = f"{chipflow_api_origin}/build/{resp_data['build_id']}/status"
                self._log_stream_url = f"{chipflow_api_origin}/build/{resp_data['build_id']}/logs?follow=true"

                sp.succeed(f"✅ Design submitted successfully! Build URL: {self._build_url}")

                exit_code = 0
                if args.wait:
                    exit_code = self._stream_logs(sp, network_err)
                if fh:
                    fh.close()
                exit(exit_code)
            else:
                # Log detailed information about the failed request
                logger.debug(f"Request failed with status code {resp.status_code}")
                logger.debug(f"Request URL: {resp.request.url}")

                # Log headers with auth information redacted
                headers = dict(resp.request.headers)
                if "Authorization" in headers:
                    headers["Authorization"] = "REDACTED"
                logger.debug(f"Request headers: {headers}")

                logger.debug(f"Request data: {data}")
                logger.debug(f"Response headers: {dict(resp.headers)}")
                logger.debug(f"Response body: {resp_data}")
                sp.text = ""
                match resp.status_code:
                    case 401 | 403:
                        sp.fail(f"💥  Authorization denied: {resp_data['message']}. It seems CHIPFLOW_API_KEY is set incorreectly!")
                    case _:
                        sp.fail(f"💥  Failed to access ChipFlow Cloud: ({resp_data['message']})")
                if fh:
                    fh.close()
                exit(2)

    def _long_poll_stream(self, sp, network_err):
        steps = self._last_log_steps
        stream_event_counter = 0
        assert self._chipflow_api_key
        # after 4 errors, return to _stream_logs loop and query the build status again
        while (stream_event_counter < 4):
            sp.text = "Build running... " + ' -> '.join(steps)
            try:
                log_resp = requests.get(
                    self._log_stream_url,
                    auth=("", self._chipflow_api_key),
                    stream=True,
                    timeout=(2.0, 60.0)  # fail if connect takes >2s, long poll for 60s at a time
                )
                if log_resp.status_code == 200:
                    for line in log_resp.iter_lines():
                        line_str = line.decode("utf-8") if line else ""
                        logger.debug(line_str)
                        match line_str[0:8]:
                            case "DEBUG   ":
                                sp.info(line_str) if log_level <= logging.DEBUG else None
                            case "INFO    ":
                                sp.info(line_str) if log_level <= logging.INFO else None
                                # Some special handling for more user feedback
                                if line_str.endswith("started"):
                                    steps = re.findall(r"([0-9a-z_.]+)\:+?", line_str[18:])[0:2]
                                    sp.text = "Build running... " + ' -> '.join(steps)
                            case "WARNING ":
                                sp.info(line_str) if log_level <= logging.WARNING else None
                            case "ERROR   ":
                                sp.info(line_str) if log_level <= logging.ERROR else None
                        sp.start()
                else:
                    stream_event_counter +=1
                    logger.debug(f"Failed to stream logs: {log_resp.text}")
                    sp.text = "💥 Failed streaming build logs. Trying again!"
                    break
            except requests.ConnectionError as e:
                if type(e.__context__) is urllib3.exceptions.ReadTimeoutError:
                    continue  #just timed out, continue long poll
                sp.text = "💥 Failed connecting to ChipFlow Cloud."
                logger.debug(f"Error while streaming logs: {e}")
                break
            except (requests.RequestException, requests.exceptions.ReadTimeout) as e:
                if type(e.__context__) is urllib3.exceptions.ReadTimeoutError:
                    continue  #just timed out, continue long poll
                sp.text = "💥 Failed streaming build logs. Trying again!"
                logger.debug(f"Error while streaming logs: {e}")
                stream_event_counter +=1
                continue

        # save steps so we coninue where we left off if we manage to reconnect
        self._last_log_steps = steps
        return stream_event_counter

    def _stream_logs(self, sp, network_err):
        sp.start("Streaming the logs...")
        # Poll the status API until the build is completed or failed
        fail_counter = 0
        timeout = 10.0
        build_status = "pending"
        stream_event_counter = 0
        self._last_log_steps = []
        assert self._chipflow_api_key is not None
        while fail_counter < 10 and stream_event_counter < 10:
            sp.text = f"Waiting for build to run... {build_status}"
            time.sleep(timeout)  # Wait before polling
            try:
                status_resp = requests.get(
                    self._build_status_url,
                    auth=("", self._chipflow_api_key),
                    timeout=timeout
                )
            except requests.exceptions.ReadTimeout as e:
                sp.text = "💥 Error connecting to ChipFlow Cloud. Trying again! "
                fail_counter += 1
                logger.debug(f"Failed to fetch build status{fail_counter} times: {e}")
                continue

            if status_resp.status_code != 200:
                sp.text = "💥 Error connecting to ChipFlow Cloud. Trying again! "
                fail_counter += 1
                logger.debug(f"Failed to fetch build status {fail_counter} times: {status_resp.text}")
                continue

            status_data = status_resp.json()
            build_status = status_data.get("status")
            logger.debug(f"Build status: {build_status}")

            sp.text = f"Polling build status... {build_status}"

            if build_status == "completed":
                sp.succeed("✅ Build completed successfully!")
                return 0
            elif build_status == "failed":
                sp.succeed("❌ Build failed.")
                return 1
            elif build_status == "running":
                stream_event_counter += self._long_poll_stream(sp, network_err)

        if fail_counter >=10 or stream_event_counter >= 10:
            sp.text = ""
            sp.fail("💥 Failed fetching build status. Perhaps you hit a network error?")
            logger.debug(f"Failed to fetch build status {fail_counter} times and failed streaming {stream_event_counter} times. Exiting.")
            return 2

    def determine_submission_name(self):
        if "CHIPFLOW_SUBMISSION_NAME" in os.environ:
            return os.environ["CHIPFLOW_SUBMISSION_NAME"]
        git_head = subprocess.check_output(
            ["git", "-C", os.environ["CHIPFLOW_ROOT"],
            "rev-parse", "--short", "HEAD"],
            encoding="ascii").rstrip()
        git_dirty = bool(subprocess.check_output(
            ["git", "-C", os.environ["CHIPFLOW_ROOT"],
            "status", "--porcelain", "--untracked-files=no"]))
        submission_name = git_head
        if git_dirty:
            logger.warning("Git tree is dirty, submitting anyway!")
            submission_name += "-dirty"
        return submission_name
