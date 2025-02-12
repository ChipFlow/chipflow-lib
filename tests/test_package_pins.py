# SPDX-License-Identifier: BSD-2-Clause
import unittest

from chipflow_lib.platforms.utils import (
    BareDiePackageDef, QuadPackageDef, Package
)


class TestBareDiePackage(unittest.TestCase):
    def setUp(self):
        self.package = BareDiePackageDef(name="test_package", width=8, height=4)

    def test_basic_properties(self):
        """Test basic package properties"""
        self.assertEqual(self.package.name, "test_package")
        self.assertEqual(self.package.width, 8)
        self.assertEqual(self.package.height, 4)
        self.assertEqual(self.package.type, "BareDiePackageDef")

    def test_bringup_pins(self):
        """Test bringup pins configuration"""
        bringup_pins = self.package.bringup_pins

        # Test that we have the required bringup pin categories
        self.assertIsNotNone(bringup_pins.core_power)
        self.assertIsNotNone(bringup_pins.core_clock)
        self.assertIsNotNone(bringup_pins.core_reset)
        self.assertIsNotNone(bringup_pins.core_heartbeat)
        self.assertIsNotNone(bringup_pins.core_jtag)

        # Test that power pins are structured correctly
        self.assertGreaterEqual(len(bringup_pins.core_power), 1)

        # Test that JTAG pins have all required signals
        jtag = bringup_pins.core_jtag
        self.assertIsNotNone(jtag.trst)
        self.assertIsNotNone(jtag.tck)
        self.assertIsNotNone(jtag.tms)
        self.assertIsNotNone(jtag.tdi)
        self.assertIsNotNone(jtag.tdo)


class TestQuadPackage(unittest.TestCase):
    def setUp(self):
        self.package = QuadPackageDef(name="test_package", width=36, height=36)

    def test_basic_properties(self):
        """Test basic package properties"""
        self.assertEqual(self.package.name, "test_package")
        self.assertEqual(self.package.width, 36)
        self.assertEqual(self.package.height, 36)
        self.assertEqual(self.package.type, "QuadPackageDef")
        self.assertTrue(self.package.allocate_jtag)  # Default should be True

    def test_bringup_pins(self):
        """Test bringup pins configuration"""
        bringup_pins = self.package.bringup_pins

        # Test that we have the required bringup pin categories
        self.assertIsNotNone(bringup_pins.core_power)
        self.assertIsNotNone(bringup_pins.core_clock)
        self.assertIsNotNone(bringup_pins.core_reset)
        self.assertIsNotNone(bringup_pins.core_heartbeat)
        self.assertIsNotNone(bringup_pins.core_jtag)

        # Test that power pins are structured correctly
        self.assertGreaterEqual(len(bringup_pins.core_power), 1)

        # Test that JTAG pins have all required signals
        jtag = bringup_pins.core_jtag
        self.assertIsNotNone(jtag.trst)
        self.assertIsNotNone(jtag.tck)
        self.assertIsNotNone(jtag.tms)
        self.assertIsNotNone(jtag.tdi)
        self.assertIsNotNone(jtag.tdo)


class TestPackage(unittest.TestCase):
    def setUp(self):
        self.package_def = BareDiePackageDef(name="test_package", width=8, height=4)
        self.package = Package(package_type=self.package_def)

    def test_package_initialization(self):
        """Test basic package initialization"""
        self.assertIsNotNone(self.package.package_type)
        self.assertEqual(self.package.package_type.name, "test_package")
        self.assertEqual(self.package.package_type.width, 8)
        self.assertEqual(self.package.package_type.height, 4)

    def test_package_type_access(self):
        """Test accessing package type properties through Package"""
        # Should be able to access package type bringup pins
        bringup_pins = self.package.package_type.bringup_pins
        self.assertIsNotNone(bringup_pins)

        # Test package discriminator
        self.assertEqual(self.package.package_type.type, "BareDiePackageDef")

        # Basic test of Package structure
        self.assertIsInstance(self.package.package_type, BareDiePackageDef)