# SPDX-License-Identifier: BSD-2-Clause
"""Tests for BlockPackageDef — the parameterized per-project package used
when ``[chipflow.silicon] package = "block"``."""

import unittest

from chipflow.packaging.standard import BlockPackageDef, _Side


class BlockPackageDefTestCase(unittest.TestCase):
    def test_pin_slots_match_perimeter(self):
        """A 5×3 block has 5 N + 5 S + 3 W + 3 E = 16 slots."""
        pkg = BlockPackageDef(name="block", width=5, height=3)
        slots = pkg._ordered_pins
        self.assertEqual(len(slots), 5 + 5 + 3 + 3)
        sides = {s for s, _ in slots}
        self.assertEqual(sides, {_Side.N, _Side.S, _Side.W, _Side.E})

    def test_does_not_reserve_bringup_slots(self):
        """Unlike chip packages, BlockPackageDef must not subtract any
        bringup pins from the available set — blocks have no I/O ring."""
        pkg = BlockPackageDef(name="block", width=4, height=4)
        # All 16 perimeter slots remain available.
        self.assertEqual(len(pkg._ordered_pins), 16)

    def test_bringup_pins_property_raises(self):
        """The abstract bringup_pins property must not be silently usable
        on a block — calling it should fail loudly."""
        pkg = BlockPackageDef(name="block", width=4, height=4)
        with self.assertRaises(NotImplementedError):
            pkg.bringup_pins

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
