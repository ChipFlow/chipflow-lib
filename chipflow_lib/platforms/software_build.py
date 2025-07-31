import sys

from pathlib import Path
from typing import List, Tuple

from doit import create_after, task_params

from ._signatures import DriverModel
from .._doit import TaskParams

BUILD_DIR = "./build/software"
RISCVCC = f"{sys.executable} -m ziglang cc -target riscv32-freestanding-musl"
CINCLUDES = f"-I. -I{BUILD_DIR}"
LINKER_SCR = f"{BUILD_DIR}/generated/sections.lds"
SOFTWARE_START = f"{BUILD_DIR}/generated/start.S"
CFLAGS = "-g -mcpu=baseline_rv32-a-c-d -mabi=ilp32 -Wl,-Bstatic,-T,"
CFLAGS += f"{LINKER_SCR},--strip-debug -static -ffreestanding -nostdlib {CINCLUDES}"


def collate_driver_list(dl: List[DriverModel]) -> Tuple[List[str], List[str]]:
    "Collates a list of `DriverModel`s and returns a pair of lists of absolute paths to sources and headers"
    sources = []
    headers = []
    for dm in dl:
        assert '_base_path' in dm
        base = dm['_base_path']
        if 'c_files' in dm:
            sources.extend([base / f for f in  dm['c_files']])
        if 'h_files' in dm:
            sources.extend([base / f for f in  dm['h_files']])
    return (sources, headers)


@task_params([
    TaskParams(name="drivers", default=list()),
    ])
def task_build_software_elf(drivers):
    sources, includes = collate_driver_list(drivers)
    sources.append(SOFTWARE_START)
    sources_str = " ".join(sources)

    return {
        "actions": [f"{RISCVCC} {CFLAGS} -o {BUILD_DIR}/software.elf {sources_str}"],
        "file_dep": sources + includes + [LINKER_SCR],
        "targets": [f"{BUILD_DIR}/software.elf"],
        "verbosity": 2
    }


@create_after(executed="build_software_elf", target_regex=".*/software\\.bin")
def task_build_software():
    return {
        "actions": [f"{sys.executable} -m ziglang objcopy -O binary "
                    f"{BUILD_DIR}/software.elf {BUILD_DIR}/software.bin"],
        "file_dep": [f"{BUILD_DIR}/software.elf"],
        "targets": [f"{BUILD_DIR}/software.bin"],
    }


def _create_build_dir():
    Path(f"{BUILD_DIR}/drivers").mkdir(parents=True, exist_ok=True)


