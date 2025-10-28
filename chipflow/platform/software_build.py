import sys


from doit import task_params

from .._doit import TaskParams
from ..software.soft_gen import SoftwareGenerator

@task_params([
    TaskParams(name="generator", default=None, type=SoftwareGenerator.model_validate_json), #type: ignore
    ])
def task_build_software_elf(generator):
    generator.generate()
    sources = [str(f) for f in generator.sources]
    includes = [str(f) for f in generator.includes]
    inc_dirs = ' '.join([f"-I{f}" for f in generator.include_dirs])
    sources_str = " ".join(sources)
    link_scr = str(generator.link_script)
    return {
        "actions": [f"{generator.compiler} {generator.cflags} {inc_dirs} -o {generator.build.build_dir}/software.elf {sources_str}"],
        "file_dep": sources + includes + [link_scr],
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



