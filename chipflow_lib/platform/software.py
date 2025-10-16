# SPDX-License-Identifier: BSD-2-Clause

import logging
import warnings

from collections import defaultdict

from amaranth import Fragment
from amaranth.hdl import UnusedElaboratable
from amaranth_soc import wishbone
from amaranth_soc.wishbone.sram import WishboneSRAM
from pydantic import TypeAdapter

from ..utils import ChipFlowError
from .io.signatures import DRIVER_MODEL_SCHEMA, DriverModel, DATA_SCHEMA, SoftwareBuild
from .io.annotate import submodule_metadata
from ..software.soft_gen import SoftwareGenerator


logger = logging.getLogger(__name__)
__all__ = []


def get_windows(wb_decoder):
    def _translate(subwindow, window, window_name, window_range):
        # Accessing a resource through a dense and then a sparse window results in very strange
        # layouts that cannot be easily represented, so reject those.
        window_start, window_stop, window_ratio = window_range
        subwindow_mmap, subwindow_name, subwindow_range = subwindow

        assert window_ratio == 1 or subwindow.width == window.data_width

        # names, path is a list of MemoryMap.Name
        if not subwindow_name:
            path = None  #ignore it
        else:
            path  = subwindow_name if window_name is None else (*window_name, subwindow_name)
        swstart, swend, swstep  = subwindow_range

        start = (swstart// window_ratio) + window_start
        end = swend  // window_ratio
        return (subwindow_mmap, path, (start, end, swstep))

    windows = list(wb_decoder.bus.memory_map.windows())
    map = defaultdict(list)
    for window, name, win_range in windows:
        if name and len(name):
            first_name = name[0]
            map[first_name].append(win_range)
        windows.extend([_translate(w, window, name, win_range) for w in window.windows()])
    return map


class SoftwarePlatform:
    def __init__(self, config):
        self._config = config

    def build(self, m, top):
        warnings.simplefilter(action="ignore", category=UnusedElaboratable)

        frag = Fragment.get(m, None)
        wb_decoder = None
        sram = None
        generators = {}
        driver_models = {}
        roms = {}
        for key in top.keys():
            for component, name, meta in submodule_metadata(frag, key):
                # logger.debug(f"{key} -> {component}, {name}, {meta.keys()}")
                annotations = meta['annotations']
                if DRIVER_MODEL_SCHEMA in annotations:
                    driver_models[name] = TypeAdapter(DriverModel).validate_python(annotations[DRIVER_MODEL_SCHEMA])

                if DATA_SCHEMA in annotations \
                and annotations[DATA_SCHEMA]['data']['type'] == "SoftwareBuild":
                    roms[name] = TypeAdapter(SoftwareBuild).validate_python(annotations[DATA_SCHEMA]['data'])

                if isinstance(component, wishbone.Decoder):
                    if wb_decoder is not None:
                        raise ChipFlowError("Multiple wishbone decoders are not currently supported, sorry! Get in touch!")
                    wb_decoder = component
                if isinstance(component, WishboneSRAM):
                    if sram is not None:
                        raise ChipFlowError("Multiple top-level SRAMs are not currently supported, sorry! Get in touch!")
                    sram = name

            windows = get_windows(wb_decoder)

            ram = windows[sram][0]
            ram_start = ram[0]
            ram_size = ram[1]-ram[0]

            for rom_component, build in roms.items():
                # TODO: This is a nasty hack. basically it works becuase we assume that CSR addresses are later than ROM..
                # Need to figure out how to tell which bus is which in `get_windows` (using regs_bus)

                rom_range = windows[rom_component][0]
                rom_start = rom_range[0]
                rom_size = rom_range[1]-rom_range[0]
                logger.debug(f"{key}.{rom_component} ROM start: {rom_start:08x}, size: {rom_size:08x}")
                logger.debug(f"{key}.{sram} RAM start: {ram_start:08x} size: {ram_size:08x}")
                sw = SoftwareGenerator(compiler_config=self._config.chipflow.software.riscv,
                                       build=build, rom_start=rom_start, rom_size=rom_size, ram_start=ram_start, ram_size=ram_size)

                for component, driver_model in driver_models.items():
                    # more of that nasty hack...
                    if component == rom_component:
                        addr = windows[component][1][0]
                    else:
                        addr = windows[component][0][0]
                    sw.add_periph(component, addr, driver_model)

                generators[key] = sw

        return generators

