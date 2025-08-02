import sys

from pathlib import Path
from typing import List, Tuple

from doit import create_after, task_params

from ._signatures import DriverModel
from .._doit import TaskParams
from ..software.soft_gen import SoftwareGenerator

BUILD_DIR = "./build/software"
RISCVCC = f"{sys.executable} -m ziglang cc -target riscv32-freestanding-musl"
CINCLUDES = f"-I. -I{BUILD_DIR}"
LINKER_SCR = f"{BUILD_DIR}/generated/sections.lds"
SOFTWARE_START = f"{BUILD_DIR}/generated/start.S"
CFLAGS = "-g -mcpu=baseline_rv32-a-c-d -mabi=ilp32 -Wl,-Bstatic,-T,"
CFLAGS += f"{LINKER_SCR},--strip-debug -static -ffreestanding -nostdlib {CINCLUDES}"


@task_params([
    TaskParams(name="generator", default=None, type=SoftwareGenerator.model_validate_json), #type: ignore
    ])
def task_build_software_elf(generator):
    sources = set([str(f) for f in generator.drivers['c_files']])
    sources |= set([str(f) for f in generator.build.user_files])
    sources.add(SOFTWARE_START)
    print(sources)
    includes = set([str(f) for f in generator.drivers['h_files']])
    inc_dirs = ' '.join([f"-I{f}" for f in generator.drivers['include_dirs']])
    print(generator.build)
    sources_str = " ".join(list(sources))

    return {
        "actions": [f"{RISCVCC} {CFLAGS} {inc_dirs} -o {generator.build.build_dir}/software.elf {sources_str}"],
        "file_dep": list(sources) + list(includes) + [LINKER_SCR],
        "targets": [f"{generator.build.build_dir}/software.elf"],
        "verbosity": 2
    }


@task_params([
    TaskParams(name="generator", default=None, type=SoftwareGenerator.model_validate_json), #type: ignore
    ])
def task_build_software(generator):
    build_dir = generator.build.build_dir
    return {
        "actions": [f"{sys.executable} -m ziglang objcopy -O binary "
                    f"{build_dir}/software.elf {build_dir}/software.bin"],
        "task_dep": ['build_software_elf'],
        "file_dep": [f"{build_dir}/software.elf"],
        "targets": [f"{build_dir}/software.bin"],
    }



