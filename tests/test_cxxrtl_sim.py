# SPDX-License-Identifier: BSD-2-Clause
"""Tests for CXXRTL simulation infrastructure."""

import shutil
import unittest
from pathlib import Path

from chipflow.sim import CxxrtlSimulator, build_cxxrtl


# Path to wb_timer in chipflow-digital-ip (relative to this repo)
WB_TIMER_SV = Path(__file__).parent.parent.parent / "chipflow-digital-ip" / "chipflow_digital_ip" / "io" / "sv_timer" / "wb_timer.sv"


def _has_yosys_slang() -> bool:
    """Check if yosys with slang plugin is available."""
    import importlib.util
    if importlib.util.find_spec("yowasp_yosys") is not None:
        return True
    if shutil.which("yosys"):
        import subprocess
        try:
            result = subprocess.run(
                ["yosys", "-m", "slang", "-p", "help read_slang"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return False


@unittest.skipUnless(_has_yosys_slang(), "yosys with slang plugin not available")
@unittest.skipUnless(WB_TIMER_SV.exists(), f"wb_timer.sv not found at {WB_TIMER_SV}")
class CxxrtlBuildTestCase(unittest.TestCase):
    """Test building CXXRTL from SystemVerilog."""

    def setUp(self):
        self.build_dir = Path("build/test_cxxrtl_sim")
        self.build_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.build_dir, ignore_errors=True)

    def test_build_wb_timer(self):
        """Test building CXXRTL library from wb_timer SystemVerilog."""
        lib_path = build_cxxrtl(
            sources=[WB_TIMER_SV],
            top_module="wb_timer",
            output_dir=self.build_dir,
        )

        self.assertTrue(lib_path.exists())
        # Check it's a valid shared library
        self.assertTrue(lib_path.stat().st_size > 0)


@unittest.skipUnless(_has_yosys_slang(), "yosys with slang plugin not available")
@unittest.skipUnless(WB_TIMER_SV.exists(), f"wb_timer.sv not found at {WB_TIMER_SV}")
class CxxrtlSimulatorTestCase(unittest.TestCase):
    """Test CXXRTL simulator functionality."""

    # Register addresses (word-addressed)
    REG_CTRL = 0x0
    REG_COMPARE = 0x1
    REG_COUNTER = 0x2
    REG_STATUS = 0x3

    # Control register bits
    CTRL_ENABLE = 1 << 0
    CTRL_IRQ_EN = 1 << 1

    @classmethod
    def setUpClass(cls):
        """Build the CXXRTL library once for all tests."""
        cls.build_dir = Path("build/test_cxxrtl_sim")
        cls.build_dir.mkdir(parents=True, exist_ok=True)

        cls.lib_path = build_cxxrtl(
            sources=[WB_TIMER_SV],
            top_module="wb_timer",
            output_dir=cls.build_dir,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.build_dir, ignore_errors=True)

    def setUp(self):
        self.sim = CxxrtlSimulator(self.lib_path, "wb_timer")

    def tearDown(self):
        self.sim.close()

    def _tick(self):
        """Perform a clock cycle."""
        self.sim.set("i_clk", 0)
        self.sim.step()
        self.sim.set("i_clk", 1)
        self.sim.step()

    def _reset(self):
        """Reset the design."""
        self.sim.set("i_rst_n", 0)
        self.sim.set("i_clk", 0)
        self._tick()
        self._tick()
        self.sim.set("i_rst_n", 1)
        self._tick()

    def _wb_write(self, addr: int, data: int):
        """Wishbone write transaction."""
        self.sim.set("i_wb_cyc", 1)
        self.sim.set("i_wb_stb", 1)
        self.sim.set("i_wb_we", 1)
        self.sim.set("i_wb_adr", addr)
        self.sim.set("i_wb_dat", data)
        self.sim.set("i_wb_sel", 0xF)

        # Clock until ack
        for _ in range(10):
            self._tick()
            if self.sim.get("o_wb_ack"):
                break

        self.sim.set("i_wb_cyc", 0)
        self.sim.set("i_wb_stb", 0)
        self.sim.set("i_wb_we", 0)
        self._tick()

    def _wb_read(self, addr: int) -> int:
        """Wishbone read transaction."""
        self.sim.set("i_wb_cyc", 1)
        self.sim.set("i_wb_stb", 1)
        self.sim.set("i_wb_we", 0)
        self.sim.set("i_wb_adr", addr)
        self.sim.set("i_wb_sel", 0xF)

        # Clock until ack
        for _ in range(10):
            self._tick()
            if self.sim.get("o_wb_ack"):
                break

        data = self.sim.get("o_wb_dat")

        self.sim.set("i_wb_cyc", 0)
        self.sim.set("i_wb_stb", 0)
        self._tick()

        return data

    def test_signal_discovery(self):
        """Test that signals are discovered correctly."""
        signals = list(self.sim.signals())
        self.assertGreater(len(signals), 0)

        # Check for expected signals
        signal_names = [name for name, _ in signals]
        self.assertIn("i_clk", signal_names)
        self.assertIn("i_rst_n", signal_names)
        self.assertIn("o_irq", signal_names)

    def test_reset(self):
        """Test reset clears state."""
        self._reset()

        ctrl = self._wb_read(self.REG_CTRL)
        self.assertEqual(ctrl, 0, "CTRL should be 0 after reset")

    def test_register_write_read(self):
        """Test register write and readback."""
        self._reset()

        # Write to COMPARE register
        self._wb_write(self.REG_COMPARE, 0x12345678)

        # Read back
        value = self._wb_read(self.REG_COMPARE)
        self.assertEqual(value, 0x12345678, "COMPARE should retain written value")

    def test_timer_counting(self):
        """Test that the timer counts when enabled."""
        self._reset()

        # Set high compare value so we don't trigger match
        self._wb_write(self.REG_COMPARE, 0xFFFFFFFF)

        # Enable timer
        self._wb_write(self.REG_CTRL, self.CTRL_ENABLE)

        # Run for some cycles
        for _ in range(20):
            self._tick()

        # Read counter - should have incremented
        counter = self._wb_read(self.REG_COUNTER)
        self.assertGreater(counter, 0, "Counter should have incremented")

    def test_compare_match_irq(self):
        """Test that compare match generates IRQ."""
        self._reset()

        # Set compare to 5
        self._wb_write(self.REG_COMPARE, 5)

        # Enable timer with IRQ
        self._wb_write(self.REG_CTRL, self.CTRL_ENABLE | self.CTRL_IRQ_EN)

        # Run until IRQ
        irq_fired = False
        for _ in range(50):
            self._tick()
            if self.sim.get("o_irq"):
                irq_fired = True
                break

        self.assertTrue(irq_fired, "IRQ should fire on compare match")

        # Check status register
        status = self._wb_read(self.REG_STATUS)
        self.assertTrue(status & 0x1, "IRQ pending flag should be set")
        self.assertTrue(status & 0x2, "Match flag should be set")


if __name__ == "__main__":
    unittest.main()
