# SPDX-License-Identifier: BSD-2-Clause
import json
import os
import tempfile
import unittest
from pathlib import Path

from chipflow.platforms import PACKAGE_DEFINITIONS
from chipflow.packaging import load_pinlock
from chipflow.packaging.lockfile import LockFile
from chipflow import ChipFlowError


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

    def test_load_pinlock_file(self):
        """Test loading a valid pins.lock file"""
        # Create a temporary directory with a sample pins.lock file
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set CHIPFLOW_ROOT to temporary directory
            old_chipflow_root = os.environ.get('CHIPFLOW_ROOT')
            os.environ['CHIPFLOW_ROOT'] = tmpdir

            # Clear the cache on ensure_chipflow_root
            from chipflow.utils import ensure_chipflow_root
            if hasattr(ensure_chipflow_root, 'root'):
                delattr(ensure_chipflow_root, 'root')

            try:
                # Create a minimal valid lockfile
                lockfile_data = {
                    "process": "sky130",
                    "package": {
                        "package_type": {
                            "package_type": "QuadPackageDef",
                            "name": "test_package",
                            "width": 10,
                            "height": 10,
                            "_power": []
                        }
                    },
                    "port_map": {
                        "ports": {}
                    },
                    "metadata": {}
                }

                lockfile_path = Path(tmpdir) / 'pins.lock'
                with open(lockfile_path, 'w') as f:
                    json.dump(lockfile_data, f, indent=2)

                # Test loading the lockfile
                lockfile = load_pinlock()

                # Validate structure
                self.assertIsInstance(lockfile, LockFile)
                self.assertEqual(str(lockfile.process), "sky130")
                self.assertIsNotNone(lockfile.package)
                self.assertIsNotNone(lockfile.port_map)
                self.assertIsInstance(lockfile.metadata, dict)

            finally:
                # Restore original CHIPFLOW_ROOT
                if old_chipflow_root is not None:
                    os.environ['CHIPFLOW_ROOT'] = old_chipflow_root
                elif 'CHIPFLOW_ROOT' in os.environ:
                    del os.environ['CHIPFLOW_ROOT']

                # Clear the cache again
                if hasattr(ensure_chipflow_root, 'root'):
                    delattr(ensure_chipflow_root, 'root')

    def test_load_pinlock_missing_file(self):
        """Test that loading fails gracefully when pins.lock doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_chipflow_root = os.environ.get('CHIPFLOW_ROOT')
            os.environ['CHIPFLOW_ROOT'] = tmpdir

            # Clear the cache on ensure_chipflow_root
            from chipflow.utils import ensure_chipflow_root
            if hasattr(ensure_chipflow_root, 'root'):
                delattr(ensure_chipflow_root, 'root')

            try:
                # Should raise ChipFlowError when pins.lock doesn't exist
                with self.assertRaises(ChipFlowError) as cm:
                    load_pinlock()

                self.assertIn("not found", str(cm.exception))
                self.assertIn("pins.lock", str(cm.exception))

            finally:
                if old_chipflow_root is not None:
                    os.environ['CHIPFLOW_ROOT'] = old_chipflow_root
                elif 'CHIPFLOW_ROOT' in os.environ:
                    del os.environ['CHIPFLOW_ROOT']

                # Clear the cache again
                if hasattr(ensure_chipflow_root, 'root'):
                    delattr(ensure_chipflow_root, 'root')

    def test_load_pinlock_malformed_file(self):
        """Test that loading fails gracefully with malformed pins.lock"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_chipflow_root = os.environ.get('CHIPFLOW_ROOT')
            os.environ['CHIPFLOW_ROOT'] = tmpdir

            # Clear the cache on ensure_chipflow_root
            from chipflow.utils import ensure_chipflow_root
            if hasattr(ensure_chipflow_root, 'root'):
                delattr(ensure_chipflow_root, 'root')

            try:
                # Create a malformed lockfile
                lockfile_path = Path(tmpdir) / 'pins.lock'
                with open(lockfile_path, 'w') as f:
                    f.write('{"invalid": "json structure"}\n')

                # Should raise ChipFlowError when pins.lock is malformed
                with self.assertRaises(ChipFlowError) as cm:
                    load_pinlock()

                self.assertIn("misformed", str(cm.exception))
                self.assertIn("pins.lock", str(cm.exception))

            finally:
                if old_chipflow_root is not None:
                    os.environ['CHIPFLOW_ROOT'] = old_chipflow_root
                elif 'CHIPFLOW_ROOT' in os.environ:
                    del os.environ['CHIPFLOW_ROOT']

                # Clear the cache again
                if hasattr(ensure_chipflow_root, 'root'):
                    delattr(ensure_chipflow_root, 'root')