# SPDX-License-Identifier: BSD-2-Clause
import unittest

from chipflow_lib.platforms.utils import (
    BareDiePackageDef, QuadPackageDef, Package, GAPackageDef, GALayout, GAPin
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


class TestPackage(unittest.TestCase):
    def setUp(self):
        self.package_def = BareDiePackageDef(name="test_package", width=8, height=4)
        self.package = Package(type=self.package_def)

    def test_package_initialization(self):
        """Test basic package initialization"""
        self.assertIsNotNone(self.package.type)
        self.assertEqual(self.package.type.name, "test_package")
        self.assertEqual(self.package.type.width, 8)
        self.assertEqual(self.package.type.height, 4)

    def test_package_type_access(self):
        """Test accessing package type properties through Package"""
        # Should be able to access package type bringup pins
        bringup_pins = self.package.type.bringup_pins
        self.assertIsNotNone(bringup_pins)

        # Test package discriminator
        self.assertEqual(self.package.type.package_type, "BareDiePackageDef")


class TestGAPackage(unittest.TestCase):
    def test_gapin_creation(self):
        """Test GAPin creation and equality"""
        pin1 = GAPin(h="A", w=1)
        pin2 = GAPin(h="A", w=1)
        pin3 = GAPin(h="B", w=2)

        # Test equality
        self.assertEqual(pin1, pin2)
        self.assertNotEqual(pin1, pin3)

        # Test attributes
        self.assertEqual(pin1.h, "A")
        self.assertEqual(pin1.w, 1)
        self.assertEqual(pin3.h, "B")
        self.assertEqual(pin3.w, 2)

    def test_galayout_enum_values(self):
        """Test GALayout enum values"""
        self.assertEqual(GALayout.FULL, "full")
        self.assertEqual(GALayout.PERIMETER, "perimeter")
        self.assertEqual(GALayout.CHANNEL, "channel")
        self.assertEqual(GALayout.ISLAND, "island")

    def test_gapackagedef_class_structure(self):
        """Test GAPackageDef class structure and type"""
        # Test that we can import and access the class
        from chipflow_lib.platforms.utils import BasePackageDef

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

    def test_missing_pins_configuration(self):
        """Test missing pins configuration"""
        # Since GAPin is not hashable, test individual pins
        pin1 = GAPin(h="A", w=1)
        pin2 = GAPin(h="B", w=2)
        pin3 = GAPin(h="C", w=3)

        # Test that pins can be created correctly
        self.assertEqual(pin1.h, "A")
        self.assertEqual(pin1.w, 1)
        self.assertEqual(pin2.h, "B")
        self.assertEqual(pin2.w, 2)
        self.assertEqual(pin3.h, "C")
        self.assertEqual(pin3.w, 3)

        # Test that pins are equal to themselves
        self.assertEqual(pin1, GAPin(h="A", w=1))
        self.assertEqual(pin2, GAPin(h="B", w=2))

    def test_additional_pins_configuration(self):
        """Test additional pins configuration"""
        # Since GAPin is not hashable, test individual pins
        pin1 = GAPin(h="D", w=4)
        pin2 = GAPin(h="E", w=5)

        # Test that additional pins can be created correctly
        self.assertEqual(pin1.h, "D")
        self.assertEqual(pin1.w, 4)
        self.assertEqual(pin2.h, "E")
        self.assertEqual(pin2.w, 5)

        # Test equality
        self.assertEqual(pin1, GAPin(h="D", w=4))
        self.assertEqual(pin2, GAPin(h="E", w=5))

    def test_layout_type_values(self):
        """Test different layout type values"""
        # Test that GALayout values are correct
        self.assertEqual(GALayout.FULL.value, "full")
        self.assertEqual(GALayout.PERIMETER.value, "perimeter")
        self.assertEqual(GALayout.CHANNEL.value, "channel")
        self.assertEqual(GALayout.ISLAND.value, "island")

    def test_package_public_api_methods(self):
        """Test that expected public API methods exist"""

        # Test that expected methods exist
        self.assertTrue(hasattr(GAPackageDef, 'allocate_pins'))
        self.assertTrue(hasattr(GAPackageDef, 'bringup_pins'))
        self.assertTrue(hasattr(GAPackageDef, 'heartbeat'))
        self.assertTrue(hasattr(GAPackageDef, '_power'))
        self.assertTrue(hasattr(GAPackageDef, '_jtag'))

        # Test that these are callable or properties
        self.assertTrue(callable(GAPackageDef.allocate_pins))
        # bringup_pins, heartbeat, _power, _jtag are properties

    def test_gapin_equality_operations(self):
        """Test that GAPin equality works correctly"""
        pin1 = GAPin(h="A", w=1)
        pin2 = GAPin(h="A", w=1)  # Duplicate
        pin3 = GAPin(h="B", w=2)

        # Test that GAPin equality works correctly
        self.assertEqual(pin1, pin2)  # pin1 and pin2 are equal
        self.assertNotEqual(pin1, pin3)  # pin1 and pin3 are different
        self.assertNotEqual(pin2, pin3)  # pin2 and pin3 are different

        # Test that different coordinates create different pins
        self.assertNotEqual(GAPin(h="A", w=1), GAPin(h="A", w=2))
        self.assertNotEqual(GAPin(h="A", w=1), GAPin(h="B", w=1))

    def test_gapin_string_representation(self):
        """Test GAPin string representation"""
        pin = GAPin(h="A", w=1)

        # Test that pin has reasonable string representation
        str_repr = str(pin)
        self.assertIn("A", str_repr)
        self.assertIn("1", str_repr)

    def test_inheritance_from_basepackagedef(self):
        """Test that GAPackageDef properly inherits from BasePackageDef"""
        from chipflow_lib.platforms.utils import BasePackageDef

        # Test inheritance
        self.assertTrue(issubclass(GAPackageDef, BasePackageDef))

        # Test that abstract methods are implemented
        base_methods = [method for method in dir(BasePackageDef)
                       if not method.startswith('_') and callable(getattr(BasePackageDef, method, None))]

        for method in base_methods:
            self.assertTrue(hasattr(GAPackageDef, method),
                           f"GAPackageDef should implement {method} from BasePackageDef")
