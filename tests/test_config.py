# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest

from chipflow_lib.config import get_dir_models, get_dir_software


class TestConfig(unittest.TestCase):
    def test_get_dir_models(self):
        """Test get_dir_models returns the correct path"""
        # Since we can't predict the absolute path, we'll check that it ends correctly
        models_dir = get_dir_models()
        self.assertTrue(models_dir.endswith("/chipflow_lib/models"))
        self.assertTrue(os.path.isdir(models_dir))

    def test_get_dir_software(self):
        """Test get_dir_software returns the correct path"""
        # Since we can't predict the absolute path, we'll check that it ends correctly
        software_dir = get_dir_software()
        self.assertTrue(software_dir.endswith("/chipflow_lib/software"))
        self.assertTrue(os.path.isdir(software_dir))
