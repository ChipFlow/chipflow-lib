# SPDX-License-Identifier: BSD-2-Clause
"""Tests for BlockPackageDef — the parameterized per-project package used
when ``[chipflow.silicon] package = "block"``."""

import unittest
from unittest.mock import MagicMock

from chipflow.packaging.standard import BlockPackageDef


class BlockPackageDefTestCase(unittest.TestCase):
    def test_pin_slots_match_perimeter(self):
        """A 5×3 block has 5+5+3+3 = 16 linear pin slots; pins 1 and 2
        are taken by clk and rst_n, leaving 14 user pins (3..16)."""
        pkg = BlockPackageDef(name="block", width=5, height=3)
        self.assertEqual(pkg._ordered_pins, list(range(3, 17)))

    def test_bringup_only_clk_and_rst(self):
        """Block bringup pins contain only clock and reset — no power
        (parent abutment), no heartbeat, no JTAG."""
        pkg = BlockPackageDef(name="block", width=4, height=4)
        bp = pkg.bringup_pins
        self.assertEqual(bp.core_clock, 1)
        self.assertEqual(bp.core_reset, 2)
        self.assertEqual(bp.core_power, [])
        self.assertIsNone(bp.core_heartbeat)
        self.assertIsNone(bp.core_jtag)
        # Bringup pins must be subtracted from the user-allocatable set.
        self.assertNotIn(1, pkg._ordered_pins)
        self.assertNotIn(2, pkg._ordered_pins)

    def test_allocate_bringup_emits_clk_and_rst(self):
        """The base ``_allocate_bringup`` must produce clk and rst_n
        PortDescs for a block — and skip power/heartbeat/JTAG, since
        those are absent from the bringup pin set."""
        pkg = BlockPackageDef(name="block", width=4, height=4)
        # _allocate_bringup reads silicon.debug only when checking for
        # heartbeat; supply a config with no debug section.
        config = MagicMock()
        config.chipflow.silicon.debug = None
        bringup = pkg._allocate_bringup(config)
        ports = bringup['bringup_pins']
        self.assertEqual(set(ports.keys()), {'clk', 'rst_n'})
        self.assertEqual(ports['clk'].pins, [1])
        self.assertEqual(ports['rst_n'].pins, [2])
        self.assertEqual(ports['clk'].type, 'clock')
        self.assertEqual(ports['rst_n'].type, 'reset')
        # rst_n is active-low: must come through inverted.
        self.assertTrue(ports['rst_n'].iomodel['invert'])

    def test_serialization_round_trip(self):
        """Block defs survive pydantic serialize/deserialize so they fit
        into LockFile / Package / bundle.zip."""
        pkg = BlockPackageDef(name="block", width=10, height=20)
        dumped = pkg.model_dump()
        self.assertEqual(dumped["package_type"], "BlockPackageDef")
        self.assertEqual(dumped["width"], 10)
        self.assertEqual(dumped["height"], 20)
        round = BlockPackageDef.model_validate(dumped)
        self.assertEqual(round.width, 10)
        self.assertEqual(round.height, 20)


if __name__ == "__main__":
    unittest.main()
