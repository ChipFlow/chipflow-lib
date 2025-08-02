# SPDX-License-Identifier: BSD-2-Clause

import sys

from collections import defaultdict
from pydantic import BaseModel
from pathlib import Path
from typing import NamedTuple, Optional

from .. import ChipFlowError
from ..platforms._signatures import DriverModel, SoftwareBuild


class Periph(NamedTuple):
    name: str
    component: str
    regs_struct: str
    address: int


class SoftwareGenerator(BaseModel):
    build: SoftwareBuild
    rom_start: int
    rom_size: int
    ram_start: int
    ram_size: int
    periphs: list[Periph] = []
    drivers: dict = defaultdict(set)
    link_script: Optional[Path] = None

    def generate(self):
        out_dir = self.build.build_dir / "generated"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"generating in {out_dir}")

        start = Path(out_dir) / "start.S"
        start.write_text(self.start)
        self.drivers['c_files'].add(start)

        lds = Path(out_dir) / "sections.lds"
        lds.write_text(self.lds)
        self.link_script = lds

        soc_h = Path(out_dir) / "soc.h"
        soc_h.write_text(self.soc_h)
        self.drivers['h_files'].add(soc_h)

        self.drivers['include_dirs'].add(out_dir)

    def add_periph(self, name, address, model: DriverModel):

        assert '_base_path' in model

        for k in ('c_files', 'h_files', 'include_dirs'):
            if k in model:
                for p in model[k]:   # type: ignore
                    print(f"adding {k} {p}")
                    if not p.is_absolute():
                        print(model['_base_path'] / p)
                        self.drivers[k].add(model['_base_path'] / p)
                    else:
                        print(p)
                        self.drivers[k].add(p)

        component = model['component']['name']  #type: ignore
        regs_struct = model['regs_struct']
        self.periphs.append(Periph(name, component, regs_struct, address))

    @property
    def compiler(self):
        return  f"{sys.executable} -m ziglang cc -target riscv32-freestanding-musl"

    @property
    def cflags(self):
        cflags = "-g -mcpu=baseline_rv32-a-c-d -mabi=ilp32 "
        cflags += "-static -ffreestanding -nostdlib "
        cflags += f"-Wl,-Bstatic,-T,{self.link_script},--strip-debug "
        cflags += f"-I{self.build.build_dir}"
        return cflags

    @property
    def sources(self):
        sources = set(self.drivers['c_files']).union(self.build.sources)
        return list(sources)

    @property
    def includes(self):
        includes = set(self.drivers['h_files']).union(self.build.includes)
        return list(includes)

    @property
    def include_dirs(self):
        inc_dirs = set(self.drivers['include_dirs']).union(self.build.include_dirs)
        return list(inc_dirs)


    @property
    def soc_h(self):
        result = "#ifndef SOC_H\n"
        result += "#define SOC_H\n\n"

        for i in self.drivers['h_files']:
            result += f'#include "{i}"\n'
        result += "\n"

        uart = None

        for n, t, r, a in self.periphs:
            if uart is None and t == "UARTPeripheral":  # first UART
                uart = n.upper()
            result += f'#define {n.upper()} ((volatile {r} *const)0x{a:08x})\n'

        result += '\n'

        if uart is not None:
            result += f'#define putc(x) uart_putc({uart}, x)\n'
            result += f'#define puts(x) uart_puts({uart}, x)\n'
            result += f'#define puthex(x) uart_puthex({uart}, x)\n'
        else:
            result += '#define putc(x) do {{ (void)x; }} while(0)\n'
            result += '#define puts(x) do {{ (void)x; }} while(0)\n'
            result += '#define puthex(x) do {{ (void)x; }} while(0)\n'

        result += "#endif\n"
        return result

    @property
    def start(self):
        return f""".section .text

start:
.globl start
_start:
.globl _start

# zero-initialize register file
addi x1, zero, 0
li x2, 0x{self.ram_start + self.ram_size:08x} # Top of stack
addi x3, zero, 0
addi x4, zero, 0
addi x5, zero, 0
addi x6, zero, 0
addi x7, zero, 0
addi x8, zero, 0
addi x9, zero, 0
addi x10, zero, 0
addi x11, zero, 0
addi x12, zero, 0
addi x13, zero, 0
addi x14, zero, 0
addi x15, zero, 0
addi x16, zero, 0
addi x17, zero, 0
addi x18, zero, 0
addi x19, zero, 0
addi x20, zero, 0
addi x21, zero, 0
addi x22, zero, 0
addi x23, zero, 0
addi x24, zero, 0
addi x25, zero, 0
addi x26, zero, 0
addi x27, zero, 0
addi x28, zero, 0
addi x29, zero, 0
addi x30, zero, 0
addi x31, zero, 0

# copy data section
la a0, _sidata
la a1, _sdata
la a2, _edata
bge a1, a2, end_init_data
loop_init_data:
lw a3, 0(a0)
sw a3, 0(a1)
addi a0, a0, 4
addi a1, a1, 4
blt a1, a2, loop_init_data
end_init_data:

# zero-init bss section
la a0, _sbss
la a1, _ebss
bge a0, a1, end_init_bss
loop_init_bss:
sw zero, 0(a0)
addi a0, a0, 4
blt a0, a1, loop_init_bss
end_init_bss:

# call main
call main
loop:
j loop
"""

    @property
    def lds(self):
        rom_start = self.rom_start + self.build.offset
        rom_size = self.rom_size - self.build.offset
        return f"""MEMORY
{{
    FLASH (rx)      : ORIGIN = 0x{rom_start:08x}, LENGTH = 0x{rom_size:08x}
    RAM (xrw)       : ORIGIN = 0x{self.ram_start:08x}, LENGTH = 0x{self.ram_size:08x}
}}

SECTIONS {{
    /* The program code and other data goes into FLASH */
    .text :
    {{
        . = ALIGN(4);
        *(.text)           /* .text sections (code) */
        *(.text*)          /* .text* sections (code) */
        *(.rodata)         /* .rodata sections (constants, strings, etc.) */
        *(.rodata*)        /* .rodata* sections (constants, strings, etc.) */
        *(.srodata)        /* .rodata sections (constants, strings, etc.) */
        *(.srodata*)       /* .rodata* sections (constants, strings, etc.) */
        . = ALIGN(4);
        _etext = .;        /* define a global symbol at end of code */
        _sidata = _etext;  /* This is used by the startup in order to initialize the .data secion */
    }} >FLASH


    /* This is the initialized data section
    The program executes knowing that the data is in the RAM
    but the loader puts the initial values in the FLASH (inidata).
    It is one task of the startup to copy the initial values from FLASH to RAM. */
    .data : AT ( _sidata )
    {{
        . = ALIGN(4);
        _sdata = .;        /* create a global symbol at data start; used by startup code in order to initialise the .data section in RAM */
        _ram_start = .;    /* create a global symbol at ram start for garbage collector */
        . = ALIGN(4);
        *(.data)           /* .data sections */
        *(.data*)          /* .data* sections */
        *(.sdata)           /* .sdata sections */
        *(.sdata*)          /* .sdata* sections */
        . = ALIGN(4);
        _edata = .;        /* define a global symbol at data end; used by startup code in order to initialise the .data section in RAM */
    }} >RAM

    /* Uninitialized data section */
    .bss :
    {{
        . = ALIGN(4);
        _sbss = .;         /* define a global symbol at bss start; used by startup code */
        *(.bss)
        *(.bss*)
        *(.sbss)
        *(.sbss*)
        *(COMMON)

        . = ALIGN(4);
        _ebss = .;         /* define a global symbol at bss end; used by startup code */
    }} >RAM

    /* this is to define the start of the heap, and make sure we have a minimum size */
    .heap :
    {{
        . = ALIGN(4);
        _heap_start = .;    /* define a global symbol at heap start */
    }} >RAM
}}
"""  # nopep8
