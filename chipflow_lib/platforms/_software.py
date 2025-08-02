# SPDX-License-Identifier: BSD-2-Clause

import logging
import warnings

from collections import defaultdict
from pathlib import Path
from pprint import pformat

from amaranth import Fragment
from amaranth.hdl import UnusedElaboratable
from amaranth.lib import wiring
from amaranth_soc import wishbone
from pydantic import TypeAdapter

from .. import _ensure_chipflow_root, ChipFlowError
from ._signatures import DRIVER_MODEL_SCHEMA, DATA_SCHEMA, DriverModel, Data, SoftwareBuild
from ..software.soft_gen import SoftwareGenerator


logger = logging.getLogger(__name__)
__all__ = []


def get_windows(wb_decoder):
    def _translate(subwindow, window, window_name, window_range):
        # Accessing a resource through a dense and then a sparse window results in very strange
        # layouts that cannot be easily represented, so reject those.
        assert window_range[2] == 1 or subwindow.width == window.data_width
        if not subwindow[1]:
            path = None  #ignore it
        else:
            path  = subwindow[1] if window_name is None else (window_name[0], subwindow[1])
        swstart = subwindow[2][0]
        swend = subwindow[2][1]
        swstep = subwindow[2][2]
        end = swend  // window_range[2]
        start = (swstart// window_range[2]) + window_range[0]
        width = (swstart - swend) * window_range[2]
        return (subwindow[0], path, (start, end, swstep))

    windows = list(wb_decoder.bus.memory_map.windows())
    map = defaultdict(list)
    for window, name, win_range in windows:
        if name:
            map[name].append(win_range)
        sws = list(window.windows())
        windows.extend([_translate(w, window, name, win_range) for w in sws ])
    return map


class SoftwarePlatform:
    def __init__(self, config):
        self._config = config

    def build(self, e, top):
        warnings.simplefilter(action="ignore", category=UnusedElaboratable)

        frag = Fragment.get(e, None)

        print(frag.subfragments)

        wb_decoder = None

        generators = {}
        driver_models = {}
        data = {}
        for key in top.keys():
            subfrag = frag.find_subfragment(key)
            design = subfrag.prepare()
            for k,v in design.elaboratables.items():
                name = design.fragments[design.elaboratables[k]].name[1:]
                if isinstance(k, wiring.Component):
                    annotations = k.metadata.as_json()['interface']['annotations']
                    if DRIVER_MODEL_SCHEMA in annotations:
                        driver_models[name] = TypeAdapter(DriverModel).validate_python(annotations[DRIVER_MODEL_SCHEMA])

                    if DATA_SCHEMA in annotations and annotations[DATA_SCHEMA]['data']['type'] == "SoftwareBuild":
                        data[name] = TypeAdapter(SoftwareBuild).validate_python(annotations[DATA_SCHEMA]['data'])

                if isinstance(k, wishbone.Decoder):
                    if wb_decoder is not None:
                        raise ChipFlowError("Multiple wishbone decoders are not currently supported, sorry! Get in touch!")
                    wb_decoder = k
            windows = get_windows(wb_decoder)


            print(f"data: {data}")

            # TODO we currently assume main ram is called 'sram' :/ Annotate?

            ram = windows[('sram',)][0]
            ram_start = ram[0]
            ram_size = ram[1]-ram[0]

            for component, build in data.items():

                # TODO: This is a nasty hack. Need to a) decorate spiflash in such a way that we can determine
                # which window is ROM and also should have an image generated for it, and b) figure out
                # how to tell which bus is which in `get_windows`

                rom = windows[component][0]
                rom_start = rom[0]
                rom_size = rom[1]-rom[0]
                print(f"ROM location: {rom[0]:x}, {rom[1]:x}")
                print(f"RAM location: {ram[0]:x}, {ram[1]:x}")
                sw = SoftwareGenerator(build=build, rom_start=rom_start, rom_size=rom_size, ram_start=ram_start, ram_size=ram_size)

                for k,v in driver_models.items():
                    addr = windows[k][0][0]
                    name = '_'.join(k)
                    sw.add_periph(name, addr, v)

                generators[key] = sw

        return generators

