# SPDX-License-Identifier: BSD-2-Clause
import unittest

from chipflow_lib.platforms import PACKAGE_DEFINITIONS


class TestPinLock(unittest.TestCase):
    def test_package_definitions_available(self):
        """Test that package definitions are available for pin locking"""
        self.assertIsInstance(PACKAGE_DEFINITIONS, dict)
        self.assertIn('pga144', PACKAGE_DEFINITIONS)
        self.assertIn('cf20', PACKAGE_DEFINITIONS)

    def test_package_definitions_structure(self):
        """Test that package definitions have basic structure needed for pin locking"""
        for name, package_def in PACKAGE_DEFINITIONS.items():
            self.assertIsNotNone(package_def)
            self.assertTrue(hasattr(package_def, 'name'))
            # Package names might have different cases
            self.assertEqual(package_def.name.lower(), name.lower())
            # Package definitions should have allocation methods
            self.assertTrue(hasattr(package_def, 'allocate_pins'))
            self.assertTrue(callable(package_def.allocate_pins))