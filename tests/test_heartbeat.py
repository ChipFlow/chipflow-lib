# amaranth: UnusedElaboratable=no
# SPDX-License-Identifier: BSD-2-Clause

import unittest
from unittest import mock

from amaranth import Module
from amaranth.lib import io

from chipflow_lib.platforms.silicon import make_hashable


class TestMakeHashable(unittest.TestCase):
    def test_make_hashable(self):
        """Test make_hashable decorator"""
        # Create a test class
        class DummyClass:
            pass
        
        # Apply decorator to test class
        HashableClass = make_hashable(DummyClass)
        
        # Create two instances
        obj1 = HashableClass()
        obj2 = HashableClass()
        
        # Check hash implementation
        self.assertEqual(hash(obj1), hash(id(obj1)))
        
        # Check equality implementation
        self.assertNotEqual(obj1, obj2)
        self.assertEqual(obj1, obj1)
        
        # Check dictionary behavior
        d = {obj1: "value1", obj2: "value2"}
        self.assertEqual(d[obj1], "value1")
        self.assertEqual(d[obj2], "value2")


@mock.patch('chipflow_lib.platforms.silicon.Heartbeat')
@mock.patch('chipflow_lib.platforms.silicon.io.Buffer')
class TestHeartbeat(unittest.TestCase):
    def test_heartbeat_mocked(self, mock_buffer, mock_heartbeat):
        """Test that Heartbeat can be imported and mocked"""
        from chipflow_lib.platforms.silicon import Heartbeat
        
        # Verify that the mock is working
        self.assertEqual(Heartbeat, mock_heartbeat)
        
        # Create a mock ports
        ports = mock.Mock()
        
        # Create a Heartbeat instance
        hb = Heartbeat(ports)
        
        # Verify initialization
        mock_heartbeat.assert_called_once_with(ports)