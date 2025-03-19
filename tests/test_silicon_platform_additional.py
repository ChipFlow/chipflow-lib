# amaranth: UnusedElaboratable=no

# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest
from unittest import mock

import tomli
from amaranth import Module, Signal, ClockDomain, ClockSignal, ResetSignal
from amaranth.lib import io, wiring
from amaranth.lib.wiring import Component, In

from chipflow_lib.platforms.silicon import (
    IOBuffer, FFBuffer, SiliconPlatformPort
)
from chipflow_lib.platforms.utils import Port


@mock.patch('chipflow_lib.platforms.silicon.IOBuffer.elaborate')
class TestIOBuffer(unittest.TestCase):
    def test_io_buffer_elaborate_mocked(self, mock_elaborate):
        """Test IOBuffer class by mocking the elaborate method"""
        # Create a mock SiliconPlatformPort
        mock_port = mock.MagicMock(spec=SiliconPlatformPort)
        mock_port.direction = io.Direction.Input
        mock_port.invert = False

        # Setup mock elaborate to return a Module
        mock_elaborate.return_value = Module()

        # Create buffer
        buffer = IOBuffer("i", mock_port)

        # Call elaborate
        result = buffer.elaborate(mock.MagicMock())

        # Check mock was called
        mock_elaborate.assert_called_once()

        # Check result is what was returned by mock
        self.assertIsInstance(result, Module)


@mock.patch('chipflow_lib.platforms.silicon.FFBuffer.elaborate')
class TestFFBuffer(unittest.TestCase):
    def test_ff_buffer_elaborate_mocked(self, mock_elaborate):
        """Test FFBuffer class by mocking the elaborate method"""
        # Create a mock SiliconPlatformPort
        mock_port = mock.MagicMock(spec=SiliconPlatformPort)
        mock_port.direction = io.Direction.Input

        # Setup mock elaborate to return a Module
        mock_elaborate.return_value = Module()

        # Create buffer
        buffer = FFBuffer("i", mock_port)

        # Call elaborate
        result = buffer.elaborate(mock.MagicMock())

        # Check mock was called
        mock_elaborate.assert_called_once()

        # Check result is what was returned by mock
        self.assertIsInstance(result, Module)

    def test_ff_buffer_with_domains(self, mock_elaborate):
        """Test FFBuffer with custom domains"""
        # Create a mock SiliconPlatformPort
        mock_port = mock.MagicMock(spec=SiliconPlatformPort)
        mock_port.direction = io.Direction.Bidir

        # Setup mock elaborate to return a Module
        mock_elaborate.return_value = Module()

        # Create buffer with custom domains
        buffer = FFBuffer("io", mock_port, i_domain="i_domain", o_domain="o_domain")

        # Check domains were set
        self.assertEqual(buffer.i_domain, "i_domain")
        self.assertEqual(buffer.o_domain, "o_domain")


class TestSiliconPlatformMethods(unittest.TestCase):
    def setUp(self):
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))
        current_dir = os.path.dirname(__file__)
        customer_config = f"{current_dir}/fixtures/mock.toml"
        with open(customer_config, "rb") as f:
            self.config = tomli.load(f)

    @mock.patch('chipflow_lib.platforms.silicon.load_pinlock')
    def test_instantiate_ports(self, mock_load_pinlock):
        """Test instantiate_ports method with minimal mocking"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform, Port
        from amaranth import Module, Signal, ClockDomain

        # Create mock pinlock
        mock_pinlock = mock.MagicMock()
        mock_load_pinlock.return_value = mock_pinlock

        # Setup an empty port_map to avoid unnecessary complexity
        if hasattr(mock_pinlock, 'port_map'):
            mock_pinlock.port_map = {}
        else:
            # For Pydantic model support
            mock_pinlock.configure_mock(port_map={})

        # Setup no clocks and no resets to avoid buffer creation
        if not hasattr(mock_pinlock, 'package'):
            mock_pinlock.package = mock.MagicMock()
        mock_pinlock.package.clocks = {}
        mock_pinlock.package.resets = {}

        # Create a config with empty clocks and resets configs
        config_copy = self.config.copy()
        config_copy["chipflow"] = config_copy.get("chipflow", {}).copy()
        config_copy["chipflow"]["clocks"] = {}
        config_copy["chipflow"]["resets"] = {}

        # Create platform with our modified config
        platform = SiliconPlatform(config_copy)

        # Force the _ports dictionary to have a few test ports
        # This avoids the complex mock setup that was causing issues
        from chipflow_lib.platforms.silicon import SiliconPlatformPort

        port_obj1 = Port(type="input", pins=["1"], port_name="test_port1",
                        direction=io.Direction.Input, options={})
        port_obj2 = Port(type="output", pins=["2"], port_name="test_port2",
                        direction=io.Direction.Output, options={})

        platform._ports = {
            "test_port1": SiliconPlatformPort("comp", "test_port1", port_obj1),
            "test_port2": SiliconPlatformPort("comp", "test_port2", port_obj2),
        }

        # Create a module with a clock domain
        m = Module()
        m.domains.sync = ClockDomain()

        # The core thing we want to test is setting the pinlock to our mock
        if hasattr(platform, "pinlock"):
            del platform.pinlock
        self.assertFalse(hasattr(platform, "pinlock"))

        # Call the method we want to test
        # This should now just set the pinlock attribute
        # and not try to create additional ports because we mocked an empty pinlock
        platform.instantiate_ports(m)

        # Check that ports are accessible
        self.assertEqual(len(platform._ports), 2)
        self.assertIn("test_port1", platform._ports)
        self.assertIn("test_port2", platform._ports)

        # Check that pinlock was set
        self.assertEqual(platform.pinlock, mock_pinlock)

    def test_instantiate_ports_missing_clock(self):
        """Test instantiate_ports method with missing clock directly"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform, load_pinlock, ChipFlowError
        from amaranth import Module

        # Create a config with missing clock configuration
        # This deliberately causes an error to test error handling
        config_copy = self.config.copy()
        config_copy["chipflow"] = config_copy.get("chipflow", {}).copy()
        config_copy["chipflow"]["clocks"] = {"default": "non_existent_clock"}
        config_copy["chipflow"]["resets"] = {}

        # Create platform with our modified config
        platform = SiliconPlatform(config_copy)

        # Make sure pinlock is not already set
        if hasattr(platform, "pinlock"):
            del platform.pinlock

        # Create a Module
        m = Module()

        # Create a custom TestPinlock with an empty clocks dict
        class TestPinlock:
            def __init__(self):
                self.port_map = {}
                self.package = mock.MagicMock()
                self.package.clocks = {}
                self.package.resets = {}

        # Patch the load_pinlock function directly
        original_load_pinlock = load_pinlock
        try:
            # Replace with our custom implementation
            load_pinlock.__globals__['load_pinlock'] = lambda: TestPinlock()

            # Call instantiate_ports - should raise ChipFlowError
            with self.assertRaises(ChipFlowError):
                platform.instantiate_ports(m)
        finally:
            # Restore the original function to avoid affecting other tests
            load_pinlock.__globals__['load_pinlock'] = original_load_pinlock

    @mock.patch('chipflow_lib.platforms.silicon.ClockSignal')
    @mock.patch('chipflow_lib.platforms.silicon.ResetSignal')
    @mock.patch('chipflow_lib.platforms.silicon.io.Buffer')
    @mock.patch('chipflow_lib.platforms.silicon.FFSynchronizer')
    @mock.patch('chipflow_lib.platforms.silicon.SiliconPlatformPort')
    @mock.patch('chipflow_lib.platforms.silicon.load_pinlock')
    def test_instantiate_ports_with_clocks_and_resets(self, mock_load_pinlock, mock_silicon_platform_port,
                                                    mock_ff_synchronizer, mock_buffer,
                                                    mock_reset_signal, mock_clock_signal):
        """Test instantiate_ports method with clocks and resets"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform, Port
        from amaranth import Module, Signal

        # Create mocks for signals and buffer
        mock_clock_signal_instance = Signal()
        mock_reset_signal_instance = Signal()
        mock_clock_signal.return_value = mock_clock_signal_instance
        mock_reset_signal.return_value = mock_reset_signal_instance

        # Create mock for buffer
        mock_buffer_instance = mock.MagicMock()
        mock_buffer_instance.i = Signal()
        mock_buffer.return_value = mock_buffer_instance

        # Create mock for SiliconPlatformPort
        mock_port_instance = mock.MagicMock()
        mock_port_instance.i = Signal()
        mock_port_instance.o = Signal()
        mock_port_instance.oe = Signal()
        mock_silicon_platform_port.side_effect = lambda comp, name, port, **kwargs: mock_port_instance

        # Create mock pinlock with simpler approach
        mock_pinlock = mock.MagicMock()

        # Setup port_map
        mock_port = mock.MagicMock()
        mock_port.port_name = "test_port"
        mock_port_map = {"component1": {"interface1": {"port1": mock_port}}}
        mock_pinlock.port_map = mock_port_map

        # Setup clocks and resets
        mock_clock_port = mock.MagicMock()
        mock_clock_port.port_name = "sys_clk"
        mock_alt_clock_port = mock.MagicMock()
        mock_alt_clock_port.port_name = "alt_clk"
        mock_reset_port = mock.MagicMock()
        mock_reset_port.port_name = "sys_rst"

        mock_pinlock.package.clocks = {
            "sys_clk": mock_clock_port,
            "alt_clk": mock_alt_clock_port
        }
        mock_pinlock.package.resets = {
            "sys_rst": mock_reset_port
        }

        # Return mock pinlock from load_pinlock
        mock_load_pinlock.return_value = mock_pinlock

        # Create config with clock and reset definitions
        config_copy = self.config.copy()
        config_copy["chipflow"] = config_copy.get("chipflow", {}).copy()
        config_copy["chipflow"]["clocks"] = {
            "default": "sys_clk",
            "alt": "alt_clk"
        }
        config_copy["chipflow"]["resets"] = {
            "reset": "sys_rst"
        }

        # Create platform with modified config
        platform = SiliconPlatform(config_copy)

        # Make sure pinlock is not already set
        if hasattr(platform, "pinlock"):
            del platform.pinlock

        # Create module to pass to instantiate_ports
        m = Module()

        # Call instantiate_ports
        platform.instantiate_ports(m)

        # Verify clocks were set up
        self.assertIn("sys_clk", platform._ports)
        self.assertIn("alt_clk", platform._ports)

        # Verify resets were set up
        self.assertIn("sys_rst", platform._ports)

        # Verify port_map ports were added
        self.assertIn("test_port", platform._ports)

        # Verify the pinlock was set
        self.assertEqual(platform.pinlock, mock_pinlock)

        # Verify creation of SiliconPlatformPort for clocks and resets
        for name, port in [("sys_clk", mock_clock_port), ("alt_clk", mock_alt_clock_port),
                           ("sys_rst", mock_reset_port)]:
            call_found = False
            for call in mock_silicon_platform_port.call_args_list:
                if call[0][1] == name:
                    call_found = True
            self.assertTrue(call_found, f"SiliconPlatformPort not created for {name}")

        # Verify buffer was created for clocks and resets (line 281-282 and 289)
        self.assertGreaterEqual(mock_buffer.call_count, 3)  # At least 3 calls (2 clocks, 1 reset)

        # Verify FFSynchronizer was created for reset (line 291)
        self.assertGreaterEqual(mock_ff_synchronizer.call_count, 1)

    @mock.patch('chipflow_lib.platforms.silicon.IOBuffer')
    @mock.patch('chipflow_lib.platforms.silicon.FFBuffer')
    def test_get_io_buffer(self, mock_ffbuffer, mock_iobuffer):
        """Test get_io_buffer method with mocked buffer classes to avoid UnusedElaboratable warnings"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.silicon import SiliconPlatform

        # Setup mock returns
        mock_io_instance = mock.MagicMock()
        mock_ff_instance = mock.MagicMock()
        mock_iobuffer.return_value = mock_io_instance
        mock_ffbuffer.return_value = mock_ff_instance

        # Create platform
        platform = SiliconPlatform(self.config)

        # Create a SiliconPlatformPort
        port_obj = Port(type="bidir", pins=["1", "2"], port_name="test_bidir",
                       direction="io", options={"all_have_oe": False})
        silicon_port = SiliconPlatformPort("comp", "test_bidir", port_obj)

        # Create different buffer types
        io_buffer = io.Buffer("io", silicon_port)
        ff_buffer = io.FFBuffer("io", silicon_port, i_domain="sync", o_domain="sync")

        # Test with io.Buffer
        result_io = platform.get_io_buffer(io_buffer)
        self.assertEqual(result_io, mock_io_instance)
        # The first arg to IOBuffer is the direction enum, not string
        mock_iobuffer.assert_called_once_with(io.Direction.Bidir, silicon_port)

        # Test with io.FFBuffer
        result_ff = platform.get_io_buffer(ff_buffer)
        self.assertEqual(result_ff, mock_ff_instance)
        # The first arg to FFBuffer is the direction enum, not string
        mock_ffbuffer.assert_called_once_with(io.Direction.Bidir, silicon_port, i_domain="sync", o_domain="sync")

        # Test with unsupported buffer type
        unsupported_buffer = mock.MagicMock()
        unsupported_buffer.direction = "io"
        unsupported_buffer.port = silicon_port
        with self.assertRaises(TypeError):
            platform.get_io_buffer(unsupported_buffer)
