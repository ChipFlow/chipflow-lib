# SPDX-License-Identifier: BSD-2-Clause
import unittest

from chipflow_lib.errors import ChipFlowError


class TestErrors(unittest.TestCase):
    def test_chipflow_error(self):
        """Test that ChipFlowError can be instantiated and raised"""
        # Test instantiation
        error = ChipFlowError("Test error message")
        self.assertEqual(str(error), "Test error message")

        # Test raising
        with self.assertRaises(ChipFlowError) as cm:
            raise ChipFlowError("Test raised error")

        self.assertEqual(str(cm.exception), "Test raised error")

        # Test inheritance
        self.assertTrue(issubclass(ChipFlowError, Exception))
