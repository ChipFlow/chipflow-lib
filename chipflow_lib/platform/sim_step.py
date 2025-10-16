import inspect
import importlib.resources
import logging
import os
import subprocess

from contextlib import contextmanager

from doit.cmd_base import TaskLoader2, loader
from doit.doit_cmd import DoitMain
from doit.task import dict_to_task

from amaranth import Module

from .base import StepBase, _wire_up_ports
from .sim import VARIABLES, TASKS, DOIT_CONFIG, SimPlatform
from ..utils import ChipFlowError, ensure_chipflow_root, top_components


EXE = ".exe" if os.name == "nt" else ""
logger = logging.getLogger(__name__)


@contextmanager
def common():
    chipflow_lib = importlib.resources.files('chipflow_lib')
    common = chipflow_lib.joinpath('common', 'sim')
    with importlib.resources.as_file(common) as f:
        yield f

@contextmanager
def runtime():
    yowasp = importlib.resources.files("yowasp_yosys")
    runtime = yowasp.joinpath('share', 'include', 'backends', 'cxxrtl', 'runtime')
    with importlib.resources.as_file(runtime) as f:
        yield f


class ContextTaskLoader(TaskLoader2):
    def __init__(self, config, tasks, context):
        self.config = config
        self.tasks = tasks
        self.subs = context
        super().__init__()

    def load_doit_config(self):
        return loader.load_doit_config(self.config)

    def load_tasks(self, cmd, pos_args):
        task_list = []
        # substitute
        for task in self.tasks:
            d = {}
            for k,v in task.items():
                match v:
                    case str():
                        d[k.format(**self.subs)] = v.format(**self.subs)
                    case list():
                        d[k.format(**self.subs)] = [i.format(**self.subs) for i in v]
                    case _:
                        raise ChipFlowError("Unexpected task definition")
            task_list.append(dict_to_task(d))
        return task_list

class SimStep(StepBase):
    def __init__(self, config):
        self._platform = SimPlatform(config)
        self._config = config

    def build_cli_parser(self, parser):
        action_argument = parser.add_subparsers(dest="action")
        action_argument.add_parser(
            "build", help=inspect.getdoc(self.build).splitlines()[0])   # type: ignore
        action_argument.add_parser(
            "run", help=inspect.getdoc(self.run).splitlines()[0])  # type: ignore
        action_argument.add_parser(
            "check", help=inspect.getdoc(self.check).splitlines()[0])  # type: ignore

    def run_cli(self, args):
        # Import here to avoid circular dependency
        from ..packaging import load_pinlock
        load_pinlock()  # check pinlock first so we error cleanly

        match (args.action):
            case "build":
                self.build(args)
            case "run":
                self.run(args)
            case "check":
                self.check(args)

    @property
    def sim_dir(self):
        return ensure_chipflow_root() / 'build' / 'sim'

    def build(self, *args):
        """
        Builds the simulation model for the design
        """
        print("Building simulation...")
        m = Module()
        self._platform.instantiate_ports(m)

        # heartbeat led (to confirm clock/reset alive)
        #if ("debug" in self._config["chipflow"]["silicon"] and
        #   self._config["chipflow"]["silicon"]["debug"]["heartbeat"]):
        #    heartbeat_ctr = Signal(23)
        #    m.d.sync += heartbeat_ctr.eq(heartbeat_ctr + 1)
        #    m.d.comb += platform.request("heartbeat").o.eq(heartbeat_ctr[-1])

        top = top_components(self._config)
        logger.debug(f"SimStep top = {top}")

        _wire_up_ports(m, top, self._platform)

        #FIXME: common source for build dir
        self._platform.build(m, top)
        with common() as common_dir, runtime() as runtime_dir:
            context = {
                "COMMON_DIR": common_dir,
                "RUNTIME_DIR": runtime_dir,
                "PROJECT_ROOT": ensure_chipflow_root(),
                "BUILD_DIR": ensure_chipflow_root() / 'build',
                "EXE": EXE,
                }
            for k,v in VARIABLES.items():
                context[k] = v.format(**context)
            if DoitMain(ContextTaskLoader(DOIT_CONFIG, TASKS, context)).run(["build_sim"]) !=0:
                raise ChipFlowError("Failed building simulator")

    def run(self, *args):
        """
        Run the simulation. Will ensure that the simulation and the software are both built.
        """
        # Import here to avoid circular dependency
        from ..cli import run
        run(["software"])
        self.build(args)
        result = subprocess.run([self.sim_dir / "sim_soc"], cwd=self.sim_dir)

        if result.returncode != 0:
            raise ChipFlowError("Simulation failed")

    def check(self, *args):
        """
        Run the simulation and check events against reference (tests/events_reference.json). Will ensure that the simulation and the software are both built.
        """
        if not self._config.chipflow.test:
            raise ChipFlowError("No [chipflow.test] section found in configuration")
        if not self._config.chipflow.test.event_reference:
            raise ChipFlowError("No event_reference configuration found in [chipflow.test]")

        self.run(args)
        # Import here to avoid circular import
        from ..steps._json_compare import compare_events
        compare_events(self._config.chipflow.test.event_reference, self.sim_dir / "events.json")
        print("Integration test passed sucessfully")

