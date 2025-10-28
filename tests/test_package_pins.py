# SPDX-License-Identifier: BSD-2-Clause
import unittest

from chipflow.platforms import PACKAGE_DEFINITIONS


class TestPackageDefinitions(unittest.TestCase):
    def test_package_definitions_available(self):
        """Test that package definitions are available through public API"""
        self.assertIsInstance(PACKAGE_DEFINITIONS, dict)
        self.assertIn('pga144', PACKAGE_DEFINITIONS)
        self.assertIn('cf20', PACKAGE_DEFINITIONS)

    def test_package_definitions_structure(self):
        """Test basic structure of package definitions"""
        for name, package_def in PACKAGE_DEFINITIONS.items():
            self.assertIsNotNone(package_def)
            self.assertTrue(hasattr(package_def, 'name'))
            # Package names might have different cases
            self.assertEqual(package_def.name.lower(), name.lower())