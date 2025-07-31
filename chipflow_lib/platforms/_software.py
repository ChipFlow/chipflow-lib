# SPDX-License-Identifier: BSD-2-Clause

import logging

from pathlib import Path
from pprint import pformat

from amaranth import Fragment

from .. import _ensure_chipflow_root
from ._signatures import DRIVER_MODEL_SCHEMA


logger = logging.getLogger(__name__)
__all__ = []


class SoftwarePlatform:
    def __init__(self, config):
        self.build_dir = _ensure_chipflow_root() / 'build' / 'software'
        self._config = config
        self._driver_model = {}

    def build(self, e, top):
        Path(self.build_dir).mkdir(parents=True, exist_ok=True)

        Fragment.get(e, None)

        metadata = {}
        for key in top.keys():
            metadata[key] = getattr(e.submodules, key).metadata.as_json()
        for component, iface in metadata.items():
            for interface, interface_desc in iface['interface']['members'].items():
                print(f"inspecting {interface}, {interface_desc}")
                annotations = interface_desc['annotations']

                if DRIVER_MODEL_SCHEMA in annotations:
                    self._driver_model[interface] = annotations[DRIVER_MODEL_SCHEMA]
        print(pformat(self._driver_model))


#        env = Environment(
#            loader=PackageLoader("chipflow_lib", "common/sim"),
#            autoescape=select_autoescape()
#        )
#        template = env.get_template("main.cc.jinja")
#
#        with main.open("w") as main_file:
#            print(template.render(
#                    includes = [hpp for b in self._builders if b.hpp_files for hpp in b.hpp_files ],
#                    initialisers = [exp for exp in self._top_sim.values()],
#                    interfaces = [exp for exp in self._top_sim.keys()],
#                    clocks = [cxxrtlmangle(f"io${clk}$i") for clk in self._clocks.keys()],
#                    resets = [cxxrtlmangle(f"io${rst}$i") for rst in self._resets.keys()],
#                    data_load = data_load
#                ),
#                file=main_file)
#

