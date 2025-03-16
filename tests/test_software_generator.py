# SPDX-License-Identifier: BSD-2-Clause
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chipflow_lib.software.soft_gen import SoftwareGenerator


class TestSoftwareGenerator(unittest.TestCase):
    def setUp(self):
        """Set up the test with a SoftwareGenerator instance"""
        self.rom_start = 0x10000000
        self.rom_size = 0x8000
        self.ram_start = 0x20000000
        self.ram_size = 0x4000
        self.generator = SoftwareGenerator(
            rom_start=self.rom_start,
            rom_size=self.rom_size,
            ram_start=self.ram_start,
            ram_size=self.ram_size
        )

    def test_initialization(self):
        """Test that the SoftwareGenerator initializes correctly"""
        self.assertEqual(self.generator.rom_start, self.rom_start)
        self.assertEqual(self.generator.rom_size, self.rom_size)
        self.assertEqual(self.generator.ram_start, self.ram_start)
        self.assertEqual(self.generator.ram_size, self.ram_size)
        self.assertEqual(self.generator.defines, [])
        self.assertEqual(self.generator.periphs, [])
        self.assertEqual(self.generator.extra_init, [])

    def test_add_periph(self):
        """Test adding peripherals"""
        self.generator.add_periph("uart", "uart0", 0x40000000)
        self.generator.add_periph("gpio", "gpio0", 0x40001000)

        self.assertEqual(len(self.generator.periphs), 2)
        self.assertEqual(self.generator.periphs[0], ("uart", "uart0", 0x40000000))
        self.assertEqual(self.generator.periphs[1], ("gpio", "gpio0", 0x40001000))

    def test_add_extra_init(self):
        """Test adding extra initialization code"""
        init_code = "# This is a test init code"
        self.generator.add_extra_init(init_code)

        self.assertEqual(len(self.generator.extra_init), 1)
        self.assertEqual(self.generator.extra_init[0], init_code)

    def test_soc_h_with_uart(self):
        """Test soc.h generation with a UART peripheral"""
        self.generator.add_periph("uart", "uart0", 0x40000000)

        soc_h = self.generator.soc_h

        # Check that the UART header is included
        self.assertIn('#include "drivers/uart.h"', soc_h)

        # Check that the UART is defined
        self.assertIn('#define uart0 ((volatile uart_regs_t *const)0x40000000)', soc_h)

        # Check that putc, puts, and puthex are defined to use uart0
        self.assertIn('#define putc(x) uart_putc(uart0, x)', soc_h)
        self.assertIn('#define puts(x) uart_puts(uart0, x)', soc_h)
        self.assertIn('#define puthex(x) uart_puthex(uart0, x)', soc_h)

    def test_soc_h_without_uart(self):
        """Test soc.h generation without a UART peripheral"""
        self.generator.add_periph("gpio", "gpio0", 0x40001000)

        soc_h = self.generator.soc_h

        # Check that the GPIO header is included
        self.assertIn('#include "drivers/gpio.h"', soc_h)

        # Check that the GPIO is defined
        self.assertIn('#define gpio0 ((volatile gpio_regs_t *const)0x40001000)', soc_h)

        # Check that putc, puts, and puthex are defined as no-ops
        self.assertIn('#define putc(x) do {{ (void)x; }} while(0)', soc_h)
        self.assertIn('#define puts(x) do {{ (void)x; }} while(0)', soc_h)
        self.assertIn('#define puthex(x) do {{ (void)x; }} while(0)', soc_h)

    def test_start_assembly(self):
        """Test start.S generation"""
        init_code = "# Custom initialization"
        self.generator.add_extra_init(init_code)

        start_code = self.generator.start

        # Check that the stack pointer is set to the top of RAM
        self.assertIn(f"li x2, 0x{self.ram_start + self.ram_size:08x}", start_code)

        # Check that our custom initialization code is included
        self.assertIn(init_code, start_code)

        # Check essential parts of the startup code
        self.assertIn("call main", start_code)
        self.assertIn("loop:", start_code)

    def test_linker_script(self):
        """Test sections.lds generation"""
        lds = self.generator.lds

        # Check memory regions
        self.assertIn(f"FLASH (rx)      : ORIGIN = 0x{self.rom_start:08x}, LENGTH = 0x{self.rom_size:08x}", lds)
        self.assertIn(f"RAM (xrw)       : ORIGIN = 0x{self.ram_start:08x}, LENGTH = 0x{self.ram_size:08x}", lds)

        # Check essential sections
        self.assertIn(".text :", lds)
        self.assertIn(".data :", lds)
        self.assertIn(".bss :", lds)
        self.assertIn(".heap :", lds)

    def test_generate(self):
        """Test file generation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate the files
            self.generator.generate(temp_dir)

            # Check that the files were created
            self.assertTrue(os.path.exists(os.path.join(temp_dir, "start.S")))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, "sections.lds")))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, "soc.h")))

            # Verify the content of the files
            with open(os.path.join(temp_dir, "start.S"), "r") as f:
                self.assertEqual(f.read(), self.generator.start)

            with open(os.path.join(temp_dir, "sections.lds"), "r") as f:
                self.assertEqual(f.read(), self.generator.lds)

            with open(os.path.join(temp_dir, "soc.h"), "r") as f:
                self.assertEqual(f.read(), self.generator.soc_h)