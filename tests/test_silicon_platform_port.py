# SPDX-License-Identifier: BSD-2-Clause
import unittest

from chipflow.platforms.silicon import SiliconPlatformPort


class TestSiliconPlatformPort(unittest.TestCase):
    def test_silicon_platform_port_available(self):
        """Test that SiliconPlatformPort is available in the public API"""
        # Since SiliconPlatformPort requires PortDesc which is not in the public API,
        # we can only test that the class is importable
        self.assertTrue(hasattr(SiliconPlatformPort, '__init__'))
        self.assertTrue(callable(SiliconPlatformPort))

    def test_silicon_platform_port_is_class(self):
        """Test basic class properties"""
        self.assertTrue(isinstance(SiliconPlatformPort, type))
        self.assertTrue(issubclass(SiliconPlatformPort, object))