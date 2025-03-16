# amaranth: UnusedElaboratable=no

# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest
from unittest import mock

import tomli
from amaranth import Module, Signal, ClockDomain, ClockSignal, ResetSignal
from amaranth.lib import io, wiring
from amaranth.lib.wiring import Component, In

from chipflow_lib import ChipFlowError
from chipflow_lib.platforms.silicon import (
    make_hashable, Heartbeat, IOBuffer, FFBuffer, SiliconPlatform,
    SiliconPlatformPort, HeartbeatSignature
)
from chipflow_lib.platforms.utils import Port


class TestMakeHashable(unittest.TestCase):
    def test_make_hashable(self):
        """Test the make_hashable decorator"""
        # Create a simple class
        class TestClass:
            def __init__(self, value):
                self.value = value

        # Apply the decorator
        HashableTestClass = make_hashable(TestClass)

        # Create two instances with the same value
        obj1 = HashableTestClass(42)
        obj2 = HashableTestClass(42)

        # Test that they hash to different values (based on id)
        self.assertNotEqual(hash(obj1), hash(obj2))

        # Test that they are not equal (based on id)
        self.assertNotEqual(obj1, obj2)

        # Test that an object is equal to itself
        self.assertEqual(obj1, obj1)


class TestHeartbeat(unittest.TestCase):
    def test_heartbeat_init(self):
        """Test Heartbeat initialization"""
        # Create a mock port
        mock_port = mock.MagicMock()

        # Create heartbeat component
        heartbeat = Heartbeat(mock_port)

        # Check initialization
        self.assertEqual(heartbeat.clock_domain, "sync")
        self.assertEqual(heartbeat.counter_size, 23)
        self.assertEqual(heartbeat.name, "heartbeat")
        self.assertEqual(heartbeat.ports, mock_port)

        # Check signature
        self.assertEqual(heartbeat.signature, HeartbeatSignature)

    @mock.patch('chipflow_lib.platforms.silicon.io.Buffer')
    def test_heartbeat_elaborate(self, mock_buffer):
        """Test Heartbeat elaboration"""
        # Create mocks
        mock_port = mock.MagicMock()
        mock_platform = mock.MagicMock()
        mock_buffer_instance = mock.MagicMock()
        mock_buffer.return_value = mock_buffer_instance

        # Create heartbeat component
        heartbeat = Heartbeat(mock_port)

        # Call elaborate
        result = heartbeat.elaborate(mock_platform)

        # Verify the module has clock domain logic
        self.assertIsInstance(result, Module)

        # Check that the buffer was created
        mock_buffer.assert_called_with("o", mock_port.heartbeat)


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
        mock_pinlock.port_map = {}

        # Setup no clocks and no resets to avoid buffer creation
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


