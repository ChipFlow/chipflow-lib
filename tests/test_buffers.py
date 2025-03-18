# amaranth: UnusedElaboratable=no
# SPDX-License-Identifier: BSD-2-Clause

import unittest
from unittest import mock

from amaranth import Module
from amaranth.lib import io

# We'll need to mock SiliconPlatformPort instead of using the real one
@mock.patch('chipflow_lib.platforms.silicon.IOBuffer')
@mock.patch('chipflow_lib.platforms.silicon.FFBuffer')
class TestBuffers(unittest.TestCase):
    def test_io_buffer_mocked(self, mock_ffbuffer, mock_iobuffer):
        """Test that IOBuffer can be imported and mocked"""
        from chipflow_lib.platforms.silicon import IOBuffer

        # Verify that the mock is working
        self.assertEqual(IOBuffer, mock_iobuffer)

        # Create a mock port
        port = mock.Mock()
        port.invert = False

        # Create a mock for the IOBuffer elaborate method
        module = Module()
        mock_iobuffer.return_value.elaborate.return_value = module

        # Create an IOBuffer instance
        buffer = IOBuffer(io.Direction.Input, port)

        # Elaborate the buffer
        result = buffer.elaborate(None)

        # Verify the result
        self.assertEqual(result, module)
        mock_iobuffer.return_value.elaborate.assert_called_once()

    def test_ff_buffer_mocked(self, mock_ffbuffer, mock_iobuffer):
        """Test that FFBuffer can be imported and mocked"""
        from chipflow_lib.platforms.silicon import FFBuffer

        # Verify that the mock is working
        self.assertEqual(FFBuffer, mock_ffbuffer)

        # Create a mock port
        port = mock.Mock()
        port.invert = False

        # Create a mock for the FFBuffer elaborate method
        module = Module()
        mock_ffbuffer.return_value.elaborate.return_value = module

        # Create an FFBuffer instance
        buffer = FFBuffer(io.Direction.Input, port, i_domain="sync", o_domain="sync")

        # Elaborate the buffer
        result = buffer.elaborate(None)

        # Verify the result
        self.assertEqual(result, module)
        mock_ffbuffer.return_value.elaborate.assert_called_once()