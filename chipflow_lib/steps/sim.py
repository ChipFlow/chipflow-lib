import os
import importlib.resources
import logging

from contextlib import contextmanager
from pathlib import Path
from pprint import pformat

from doit.cmd_base import TaskLoader2, loader
from doit.doit_cmd import DoitMain
from doit.task import dict_to_task

from amaranth import *

from . import StepBase, _wire_up_ports
from .. import ChipFlowError, _ensure_chipflow_root
from ..platforms import SimPlatform, top_components
from ..platforms.sim import VARIABLES, TASKS, DOIT_CONFIG


EXE = ".exe" if os.name == "nt" else ""
logger = logging.getLogger(__name__)


@contextmanager
def common():
    chipflow_lib = importlib.resources.files('chipflow_lib')
    common = chipflow_lib.joinpath('common', 'sim')
    with importlib.resources.as_file(common) as f:
        yield f

@contextmanager
def source():
    root = _ensure_chipflow_root()
    sourcedir = Path(root) / 'design' / 'sim'
    #sim_src = sourcedir.joinpath('design','sim')
    #with importlib.resources.as_file(sim_src) as f:
    yield sourcedir

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
            print(f"adding task: {pformat(d)}")
            task_list.append(dict_to_task(d))
        return task_list

class SimStep(StepBase):
    def __init__(self, config):
        self._platform = SimPlatform(config)
        self._config = config

    def build(self):
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
        self._platform.build(m)
        with common() as common_dir, source() as source_dir, runtime() as runtime_dir:
            context = {
                "COMMON_DIR": common_dir,
                "SOURCE_DIR": source_dir,
                "RUNTIME_DIR": runtime_dir,
                "PROJECT_ROOT": _ensure_chipflow_root(),
                "BUILD_DIR": _ensure_chipflow_root() / 'build',
                "EXE": EXE,
                }
            for k,v in VARIABLES.items():
                context[k] = v.format(**context)
            print(f"substituting:\n{pformat(context)}")
            DoitMain(ContextTaskLoader(DOIT_CONFIG, TASKS, context)).run(["build_sim"])
