# SPDX-License-Identifier: BSD-2-Clause
"""Tests for BlockPackageDef — the parameterized per-project package used
when ``[chipflow.silicon] package = "block"``."""

import unittest

from chipflow.packaging.standard import BlockPackageDef


class BlockPackageDefTestCase(unittest.TestCase):
    def test_pin_slots_match_perimeter(self):
        """A 5×3 block has 5+5+3+3 = 16 linear pin slots, numbered
        from 1 to 16 — same convention as QuadPackageDef."""
        pkg = BlockPackageDef(name="block", width=5, height=3)
        self.assertEqual(pkg._ordered_pins, list(range(1, 17)))

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
