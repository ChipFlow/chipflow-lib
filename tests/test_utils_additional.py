# SPDX-License-Identifier: BSD-2-Clause
import unittest

from amaranth.lib import io

from chipflow_lib.platforms import (
    IOSignature,
    IOModel,
    PACKAGE_DEFINITIONS
)


class TestIOSignature(unittest.TestCase):
    def test_pin_signature_properties(self):
        """Test IOSignature basic properties"""
        # Test with different directions
        sig_input = IOSignature(direction=io.Direction.Input, width=8)
        self.assertEqual(sig_input.direction, io.Direction.Input)
        self.assertEqual(sig_input.width, 8)

        sig_output = IOSignature(direction=io.Direction.Output, width=16)
        self.assertEqual(sig_output.direction, io.Direction.Output)
        self.assertEqual(sig_output.width, 16)

        sig_bidir = IOSignature(direction=io.Direction.Bidir, width=4)
        self.assertEqual(sig_bidir.direction, io.Direction.Bidir)
        self.assertEqual(sig_bidir.width, 4)

    def test_pin_signature_annotations(self):
        """Test IOSignature annotations method"""
        # Create signature
        sig = IOSignature(direction=io.Direction.Output, width=8, init=42)

        # Create a mock object to pass to annotations
        mock_obj = object()

        # Get annotations with the mock object
        annotations = sig.annotations(mock_obj)

        # Should return a tuple with at least one annotation
        self.assertIsInstance(annotations, tuple)
        self.assertGreater(len(annotations), 0)

        # Find annotation with PIN_ANNOTATION_SCHEMA
        pin_annotation = None
        for annotation in annotations:
            if hasattr(annotation, 'as_json'):
                json_data = annotation.as_json()
                if json_data.get('width') == 8:
                    pin_annotation = annotation
                    break

        # Verify the annotation was found and has correct values
        self.assertIsNotNone(pin_annotation, "Pin annotation not found in annotations")
        assert pin_annotation is not None
        json_data = pin_annotation.as_json()
        self.assertEqual(json_data['direction'], 'o')
        self.assertEqual(json_data['width'], 8)
        # The init field contains an Amaranth Const object, check its value
        self.assertEqual(json_data['init'], 42)


class TestIOModel(unittest.TestCase):
    def test_iomodel_basic_properties(self):
        """Test IOModel basic functionality"""
        # Test with basic properties
        iomodel = IOModel(width=8, direction=io.Direction.Input)
        self.assertEqual(iomodel['width'], 8)
        self.assertEqual(iomodel['direction'], io.Direction.Input)

        # Test with additional properties
        iomodel_with_init = IOModel(width=4, direction=io.Direction.Output, init=42)
        self.assertEqual(iomodel_with_init['width'], 4)
        self.assertEqual(iomodel_with_init['direction'], io.Direction.Output)
        self.assertEqual(iomodel_with_init['init'], 42)


class TestPackageDefinitions(unittest.TestCase):
    def test_package_definitions_exist(self):
        """Test that package definitions are available"""
        self.assertIsInstance(PACKAGE_DEFINITIONS, dict)
        self.assertGreater(len(PACKAGE_DEFINITIONS), 0)

        # Check that expected packages exist
        expected_packages = ['pga144', 'cf20']
        for package_name in expected_packages:
            self.assertIn(package_name, PACKAGE_DEFINITIONS)
            package_def = PACKAGE_DEFINITIONS[package_name]
            self.assertIsNotNone(package_def)
            self.assertTrue(hasattr(package_def, 'name'))
            self.assertEqual(package_def.name, package_name)
