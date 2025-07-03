# SPDX-License-Identifier: BSD-2-Clause
import unittest

from chipflow_lib.platforms import (
    BareDiePackageDef, QuadPackageDef, GAPackageDef
)


class TestBareDiePackage(unittest.TestCase):
    def setUp(self):
        self.package = BareDiePackageDef(name="test_package", width=8, height=4)

    def test_basic_properties(self):
        """Test basic package properties"""
        self.assertEqual(self.package.name, "test_package")
        self.assertEqual(self.package.width, 8)
        self.assertEqual(self.package.height, 4)
        self.assertEqual(self.package.package_type, "BareDiePackageDef")

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
        self.assertEqual(self.package.package_type, "QuadPackageDef")

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


class TestGAPackage(unittest.TestCase):
    def test_gapackagedef_class_structure(self):
        """Test GAPackageDef class structure and type"""
        # Test that we can import and access the class
        from chipflow_lib.platforms._utils import BasePackageDef

        # Test that GAPackageDef inherits from BasePackageDef
        self.assertTrue(issubclass(GAPackageDef, BasePackageDef))

        # Test that it has the correct type discriminator
        self.assertEqual(GAPackageDef.model_fields['package_type'].default, 'GAPackageDef')

    def test_gapackagedef_field_types(self):
        """Test GAPackageDef field definitions"""

        # Test that fields exist
        fields = GAPackageDef.model_fields
        self.assertIn('name', fields)
        self.assertIn('width', fields)
        self.assertIn('height', fields)
        self.assertIn('layout_type', fields)
        self.assertIn('channel_width', fields)
        self.assertIn('island_width', fields)
        self.assertIn('missing_pins', fields)
        self.assertIn('additional_pins', fields)

    def test_gapackagedef_pydantic_model(self):
        """Test GAPackageDef as a Pydantic model"""

        # Test that it's a Pydantic model
        import pydantic
        self.assertTrue(issubclass(GAPackageDef, pydantic.BaseModel))

        # Test that it has the expected type field in model_fields
        self.assertIn('package_type', GAPackageDef.model_fields)

    def test_package_public_api_methods(self):
        """Test that expected public API methods exist"""

        # Test that expected methods exist
        self.assertTrue(hasattr(GAPackageDef, 'bringup_pins'))

    def test_inheritance_from_basepackagedef(self):
        """Test that GAPackageDef properly inherits from BasePackageDef"""
        from chipflow_lib.platforms._utils import BasePackageDef

        # Test inheritance
        self.assertTrue(issubclass(GAPackageDef, BasePackageDef))

        # Test that abstract methods are implemented
        base_methods = [method for method in dir(BasePackageDef)
                       if not method.startswith('_') and callable(getattr(BasePackageDef, method, None))]

        for method in base_methods:
            self.assertTrue(hasattr(GAPackageDef, method),
                           f"GAPackageDef should implement {method} from BasePackageDef")
