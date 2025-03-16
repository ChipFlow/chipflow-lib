# amaranth: UnusedElaboratable=no
# SPDX-License-Identifier: BSD-2-Clause

import os
import unittest
from unittest import mock

import tomli
from amaranth import Module, Signal, Cat, ClockDomain, ClockSignal, ResetSignal
from amaranth.lib import io, wiring
from amaranth.hdl._ir import Fragment

from chipflow_lib import ChipFlowError
from chipflow_lib.platforms.silicon import (
    make_hashable, Heartbeat, IOBuffer, FFBuffer, SiliconPlatform,
    SiliconPlatformPort
)
from chipflow_lib.platforms.utils import Port


class SiliconPlatformPortTestCase(unittest.TestCase):
    def test_properties(self):
        """Test SiliconPlatformPort properties"""
        # Create port objects
        port_i = Port(type="input", pins=["1", "2"], port_name="test_input",
                     direction=io.Direction.Input, options={})
        port_o = Port(type="output", pins=["3", "4"], port_name="test_output",
                     direction=io.Direction.Output, options={})
        port_io = Port(type="bidir", pins=["5", "6"], port_name="test_bidir",
                      direction=io.Direction.Bidir, options={"all_have_oe": False})

        # Create platform ports
        plat_port_i = SiliconPlatformPort("comp", "test_input", port_i)
        plat_port_o = SiliconPlatformPort("comp", "test_output", port_o)
        plat_port_io = SiliconPlatformPort("comp", "test_bidir", port_io)

        # Test properties of input port
        self.assertEqual(plat_port_i.direction, io.Direction.Input)
        self.assertEqual(plat_port_i._direction, io.Direction.Input)
        self.assertEqual(plat_port_i.pins, ["1", "2"])
        self.assertFalse(plat_port_i.invert)

        # Test properties of output port
        self.assertEqual(plat_port_o.direction, io.Direction.Output)
        self.assertEqual(plat_port_o._direction, io.Direction.Output)
        self.assertEqual(plat_port_o.pins, ["3", "4"])
        self.assertFalse(plat_port_o.invert)

        # Test properties of bidirectional port
        self.assertEqual(plat_port_io.direction, io.Direction.Bidir)
        self.assertEqual(plat_port_io._direction, io.Direction.Bidir)
        self.assertEqual(plat_port_io.pins, ["5", "6"])
        self.assertFalse(plat_port_io.invert)

    def test_invert_property(self):
        """Test the invert property of SiliconPlatformPort"""
        # Create a port
        port = Port(type="input", pins=["1", "2"], port_name="test_input",
                   direction=io.Direction.Input, options={})

        # Create platform port with invert=True
        plat_port = SiliconPlatformPort("comp", "test_input", port, invert=True)

        # Test invert property
        self.assertTrue(plat_port.invert)
        self.assertTrue(hasattr(plat_port, "_i"))
        self.assertTrue(plat_port._o is None)
        self.assertTrue(plat_port._oe is None)

        # Test __invert__ method
        inverted_port = ~plat_port
        self.assertFalse(inverted_port.invert)
        self.assertTrue(hasattr(inverted_port, "_i"))
        self.assertTrue(inverted_port._o is None)
        self.assertTrue(inverted_port._oe is None)
        self.assertEqual(inverted_port._direction, io.Direction.Input)

        # Double invert should return to original
        double_inverted = ~inverted_port
        self.assertTrue(double_inverted.invert)
        self.assertTrue(hasattr(double_inverted, "_i"))
        self.assertTrue(double_inverted._o is None)
        self.assertTrue(double_inverted._oe is None)
        self.assertEqual(double_inverted._direction, io.Direction.Input)

    def test_getitem(self):
        """Test __getitem__ method of SiliconPlatformPort"""
        # Create ports
        port_i = Port(type="input", pins=["1", "2", "3"], port_name="test_input",
                     direction=io.Direction.Input, options={})
        port_o = Port(type="output", pins=["4", "5", "6"], port_name="test_output",
                     direction=io.Direction.Output, options={})
        port_io = Port(type="bidir", pins=["7", "8", "9"], port_name="test_bidir",
                      direction=io.Direction.Bidir, options={"all_have_oe": True})

        # Create platform ports
        plat_port_i = SiliconPlatformPort("comp", "test_input", port_i)
        plat_port_o = SiliconPlatformPort("comp", "test_output", port_o)
        plat_port_io = SiliconPlatformPort("comp", "test_bidir", port_io)

        # Make sure ports have expected attributes
        self.assertTrue(hasattr(plat_port_i, "_i"))
        self.assertTrue(hasattr(plat_port_o, "_o"))
        self.assertTrue(hasattr(plat_port_io, "_i"))
        self.assertTrue(hasattr(plat_port_io, "_o"))
        self.assertTrue(hasattr(plat_port_io, "_oe"))

        # Test input port getitem
        slice_i = plat_port_i[1]
        self.assertEqual(slice_i.direction, io.Direction.Input)
        self.assertTrue(hasattr(slice_i, "_i"))
        self.assertTrue(slice_i._o is None)
        self.assertTrue(slice_i._oe is None)

        # Test output port getitem
        slice_o = plat_port_o[0:2]
        self.assertEqual(slice_o.direction, io.Direction.Output)
        self.assertTrue(slice_o._i is None)
        self.assertTrue(hasattr(slice_o, "_o"))
        self.assertTrue(hasattr(slice_o, "_oe"))

        # Test bidir port getitem
        slice_io = plat_port_io[2]
        self.assertEqual(slice_io.direction, io.Direction.Bidir)
        self.assertTrue(hasattr(slice_io, "_i"))
        self.assertTrue(hasattr(slice_io, "_o"))
        self.assertTrue(hasattr(slice_io, "_oe"))

    def test_add(self):
        """Test __add__ method of SiliconPlatformPort"""
        # Create ports with same direction
        port_i1 = Port(type="input", pins=["1", "2"], port_name="test_input1",
                      direction=io.Direction.Input, options={})
        port_i2 = Port(type="input", pins=["3", "4"], port_name="test_input2",
                      direction=io.Direction.Input, options={})

        plat_port_i1 = SiliconPlatformPort("comp", "test_input1", port_i1)
        plat_port_i2 = SiliconPlatformPort("comp", "test_input2", port_i2)

        # Add ports
        combined = plat_port_i1 + plat_port_i2

        # Test combined port
        self.assertEqual(combined.direction, io.Direction.Input)
        self.assertEqual(len(combined), 4)

        # Create ports with different directions
        port_o = Port(type="output", pins=["5", "6"], port_name="test_output",
                     direction=io.Direction.Output, options={})
        plat_port_o = SiliconPlatformPort("comp", "test_output", port_o)

        # Adding input and output should give an error
        with self.assertRaises(ValueError):
            plat_port_i1 + plat_port_o


class IOBufferTestCase(unittest.TestCase):
    def test_elaborate_i(self):
        """Test IOBuffer elaborate with input port"""
        # Create an input port
        port_obj = Port(type="input", pins=["1", "2"], port_name="test_input",
                       direction=io.Direction.Input, options={})
        platform_port = SiliconPlatformPort("comp", "test_input", port_obj)

        # Create buffer
        buffer = IOBuffer("i", platform_port)

        # Create module and elaborate
        m = Module()
        m.submodules.buffer = buffer

        # Get the fragment
        fragment = Fragment.get(m, None)

        # Just check that elaboration succeeds without error
        self.assertIsNotNone(fragment)

    def test_elaborate_o(self):
        """Test IOBuffer elaborate with output port"""
        # Create a simple test platform
        class TestPlatform:
            pass

        # Create an output port
        port_obj = Port(type="output", pins=["1", "2"], port_name="test_output",
                       direction=io.Direction.Output, options={})
        platform_port = SiliconPlatformPort("comp", "test_output", port_obj)

        # Create buffer with the proper signals
        buffer = IOBuffer("o", platform_port)
        # Explicitly set buffer signals to match what would be set in actual use
        buffer.o = Signal(2, name="output_signal")
        buffer.oe = Signal(1, name="enable_signal", init=-1)  # Output enabled by default

        # Create module and elaborate
        m = Module()
        m.submodules.buffer = buffer

        # Get the fragment
        fragment = Fragment.get(m, TestPlatform())

        # Just check that elaboration succeeds without error
        self.assertIsNotNone(fragment)

    def test_elaborate_io(self):
        """Test IOBuffer elaborate with bidirectional port"""
        # Create a bidirectional port
        port_obj = Port(type="bidir", pins=["1", "2"], port_name="test_bidir",
                       direction=io.Direction.Bidir, options={"all_have_oe": False})
        platform_port = SiliconPlatformPort("comp", "test_bidir", port_obj)

        # Create buffer
        buffer = IOBuffer("io", platform_port)

        # Create module and elaborate
        m = Module()
        m.submodules.buffer = buffer

        # Get the fragment
        fragment = Fragment.get(m, None)

        # Just check that elaboration succeeds without error
        self.assertIsNotNone(fragment)

    def test_elaborate_invert(self):
        """Test IOBuffer elaborate with inverted port"""
        # Create an input port with invert=True
        port_obj = Port(type="input", pins=["1", "2"], port_name="test_input",
                       direction=io.Direction.Input, options={})
        platform_port = SiliconPlatformPort("comp", "test_input", port_obj, invert=True)

        # Create buffer
        buffer = IOBuffer("i", platform_port)

        # Create module and elaborate
        m = Module()
        m.submodules.buffer = buffer

        # Get the fragment
        fragment = Fragment.get(m, None)

        # Just check that elaboration succeeds without error
        self.assertIsNotNone(fragment)


class FFBufferTestCase(unittest.TestCase):
    def test_elaborate_i(self):
        """Test FFBuffer elaborate with input port"""
        # Create an input port
        port_obj = Port(type="input", pins=["1", "2"], port_name="test_input",
                       direction=io.Direction.Input, options={})
        platform_port = SiliconPlatformPort("comp", "test_input", port_obj)

        # Create buffer
        buffer = FFBuffer("i", platform_port)

        # Create module with clock domain
        m = Module()
        m.domains += ClockDomain("sync")
        m.submodules.buffer = buffer

        # Get the fragment
        fragment = Fragment.get(m, None)

        # Just check that elaboration succeeds without error
        self.assertIsNotNone(fragment)

    def test_elaborate_o(self):
        """Test FFBuffer elaborate with output port"""
        # Create a simple test platform
        class TestPlatform:
            # Mock implementation to support get_io_buffer
            def get_io_buffer(self, buffer):
                # Create a custom IOBuffer
                if isinstance(buffer, io.Buffer):
                    result = IOBuffer(buffer.direction, buffer.port)
                    # Set buffer attributes
                    if buffer.direction is not io.Direction.Output:
                        result.i = buffer.i
                    if buffer.direction is not io.Direction.Input:
                        result.o = buffer.o
                        result.oe = buffer.oe
                    return result
                return buffer

        # Create an output port
        port_obj = Port(type="output", pins=["1", "2"], port_name="test_output",
                       direction=io.Direction.Output, options={})
        platform_port = SiliconPlatformPort("comp", "test_output", port_obj)

        # Create buffer
        buffer = FFBuffer("o", platform_port)
        # Explicitly set buffer signals to match what would be set in actual use
        buffer.o = Signal(2, name="output_signal")
        buffer.oe = Signal(1, name="enable_signal", init=-1)  # Output enabled by default

        # Create module with clock domain
        m = Module()
        m.domains += ClockDomain("sync")
        m.submodules.buffer = buffer

        # Get the fragment
        fragment = Fragment.get(m, TestPlatform())

        # Just check that elaboration succeeds without error
        self.assertIsNotNone(fragment)

    def test_elaborate_io(self):
        """Test FFBuffer elaborate with bidirectional port"""
        # Create a bidirectional port
        port_obj = Port(type="bidir", pins=["1", "2"], port_name="test_bidir",
                       direction=io.Direction.Bidir, options={"all_have_oe": False})
        platform_port = SiliconPlatformPort("comp", "test_bidir", port_obj)

        # Create buffer
        buffer = FFBuffer("io", platform_port)

        # Create module with clock domain
        m = Module()
        m.domains += ClockDomain("sync")
        m.submodules.buffer = buffer

        # Get the fragment
        fragment = Fragment.get(m, None)

        # Just check that elaboration succeeds without error
        self.assertIsNotNone(fragment)

    def test_custom_domains(self):
        """Test FFBuffer with custom clock domains"""
        # Create a bidirectional port
        port_obj = Port(type="bidir", pins=["1", "2"], port_name="test_bidir",
                       direction=io.Direction.Bidir, options={"all_have_oe": False})
        platform_port = SiliconPlatformPort("comp", "test_bidir", port_obj)

        # Create buffer with custom domains
        buffer = FFBuffer("io", platform_port, i_domain="input_domain", o_domain="output_domain")

        # Check domains
        self.assertEqual(buffer.i_domain, "input_domain")
        self.assertEqual(buffer.o_domain, "output_domain")

        # Create module with clock domains
        m = Module()
        m.domains += ClockDomain("input_domain")
        m.domains += ClockDomain("output_domain")
        m.submodules.buffer = buffer

        # Get the fragment
        fragment = Fragment.get(m, None)

        # Just check that elaboration succeeds without error
        self.assertIsNotNone(fragment)


class HeartbeatTestCase(unittest.TestCase):
    def test_initialize_heartbeat(self):
        """Test Heartbeat initialization"""
        # Create a mock for ports
        mock_ports = mock.MagicMock()
        mock_ports.heartbeat = mock.MagicMock()

        # Create Heartbeat component
        heartbeat = Heartbeat(mock_ports)

        # Check initialization
        self.assertEqual(heartbeat.clock_domain, "sync")
        self.assertEqual(heartbeat.counter_size, 23)
        self.assertEqual(heartbeat.name, "heartbeat")

    def test_elaborate_heartbeat(self):
        """Test Heartbeat elaborate"""
        # Create a test platform that can handle buffer initialization
        class TestPlatform:
            def get_io_buffer(self, buffer):
                # Create specialized buffer
                if isinstance(buffer, io.Buffer):
                    result = IOBuffer(buffer.direction, buffer.port)
                else:
                    result = mock.MagicMock()

                # Set buffer attributes
                if buffer.direction is not io.Direction.Output:
                    result.i = buffer.i
                if buffer.direction is not io.Direction.Input:
                    result.o = buffer.o
                    result.oe = buffer.oe

                return result

        # Create a mock for ports that's a proper SiliconPlatformPort
        port_obj = Port(type="output", pins=["1"], port_name="heartbeat",
                       direction=io.Direction.Output, options={})

        # Create a proper SiliconPlatformPort for heartbeat
        platform_port = SiliconPlatformPort("comp", "heartbeat", port_obj)

        # Create a proper mock ports object with heartbeat attribute
        mock_ports = mock.MagicMock()
        mock_ports.heartbeat = platform_port

        # Create Heartbeat component
        heartbeat = Heartbeat(mock_ports)

        # Create module with clock domain
        m = Module()
        m.domains += ClockDomain("sync")
        m.submodules.heartbeat = heartbeat

        # Get the fragment using the test platform
        fragment = Fragment.get(m, TestPlatform())

        # Just check that elaboration succeeds without error
        self.assertIsNotNone(fragment)


class SiliconPlatformTest(unittest.TestCase):
    def setUp(self):
        # Set up environment for tests
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))
        current_dir = os.path.dirname(__file__)
        customer_config = f"{current_dir}/fixtures/mock.toml"
        with open(customer_config, "rb") as f:
            self.config = tomli.load(f)

    @mock.patch('chipflow_lib.platforms.silicon.load_pinlock')
    def test_request_port(self, mock_load_pinlock):
        """Test the request method of SiliconPlatform"""
        # Create platform
        platform = SiliconPlatform(self.config)

        # Setup ports
        test_port = mock.MagicMock()
        platform._ports = {
            "test_port": test_port
        }

        # Request existing port
        port = platform.request("test_port")
        self.assertEqual(port, test_port)

        # Request non-existent port
        with self.assertRaises(NameError):
            platform.request("non_existent_port")

        # Request port with $ in name
        with self.assertRaises(NameError):
            platform.request("bad$port")

    def test_add_file(self):
        """Test add_file method"""
        # Create platform
        platform = SiliconPlatform(self.config)

        # Test with string content
        platform.add_file("test1.v", "module test1();endmodule")
        self.assertIn("test1.v", platform._files)
        self.assertEqual(platform._files["test1.v"], b"module test1();endmodule")

        # Test with file-like object
        file_obj = mock.Mock()
        file_obj.read.return_value = "module test2();endmodule"
        platform.add_file("test2.v", file_obj)
        self.assertIn("test2.v", platform._files)
        self.assertEqual(platform._files["test2.v"], b"module test2();endmodule")

        # Test with bytes content
        platform.add_file("test3.v", b"module test3();endmodule")
        self.assertIn("test3.v", platform._files)
        self.assertEqual(platform._files["test3.v"], b"module test3();endmodule")

    @mock.patch('chipflow_lib.platforms.silicon.rtlil.convert_fragment')
    @mock.patch('chipflow_lib.platforms.silicon.os.makedirs')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('chipflow_lib.platforms.silicon.subprocess.check_call')
    def test_build(self, mock_check_call, mock_open, mock_makedirs, mock_convert_fragment):
        """Test build method with mocked dependencies"""
        # Create platform
        platform = SiliconPlatform(self.config)

        # Setup convert_fragment mock
        mock_convert_fragment.return_value = ("rtlil_code", None)

        # Add some files
        platform._files = {
            "test.v": b"module test(); endmodule",
            "test.sv": b"module test_sv(); endmodule",
            "test.vh": b"// header file"
        }

        # Create a simple module
        m = Module()

        # Call build
        result = platform.build(m, name="test_build")

        # Check that convert_fragment was called
        mock_convert_fragment.assert_called_once()

        # Check that makedirs was called to create build directory
        mock_makedirs.assert_called_once()

        # Check that check_call was called to run yowasp-yosys
        mock_check_call.assert_called_once()

        # Check that files were opened for writing
        self.assertTrue(mock_open.called)

    def test_get_io_buffer(self):
        """Test get_io_buffer method"""
        # Create platform
        platform = SiliconPlatform(self.config)

        # Create port
        port_obj = Port(type="input", pins=["1", "2"], port_name="test_input",
                       direction=io.Direction.Input, options={})
        platform_port = SiliconPlatformPort("comp", "test_input", port_obj)

        # Create buffers
        io_buffer = io.Buffer("i", platform_port)
        ff_buffer = io.FFBuffer("i", platform_port)

        # Get SiliconPlatform specialized buffers
        silicon_io_buffer = platform.get_io_buffer(io_buffer)
        silicon_ff_buffer = platform.get_io_buffer(ff_buffer)

        # Check types
        self.assertIsInstance(silicon_io_buffer, IOBuffer)
        self.assertIsInstance(silicon_ff_buffer, FFBuffer)

        # Check unsupported buffer type
        unsupported_buffer = mock.MagicMock()
        with self.assertRaises(TypeError):
            platform.get_io_buffer(unsupported_buffer)

    def test_check_clock_domains(self):
        """Test _check_clock_domains method"""
        # Create platform
        platform = SiliconPlatform(self.config)

        # Create module with sync domain
        m = Module()
        m.domains += ClockDomain("sync")

        # Get fragment
        fragment = Fragment.get(m, None)

        # Check should pass
        platform._check_clock_domains(fragment)

        # Create module with non-sync domain
        m2 = Module()
        m2.domains += ClockDomain("non_sync")

        # Get fragment
        fragment2 = Fragment.get(m2, None)

        # Check should raise error
        with self.assertRaises(ChipFlowError):
            platform._check_clock_domains(fragment2)

    def test_prepare(self):
        """Test _prepare method"""
        # Create platform
        platform = SiliconPlatform(self.config)

        # Setup some ports
        input_port = mock.MagicMock()
        input_port.direction = io.Direction.Input
        input_port.i = Signal(1)

        output_port = mock.MagicMock()
        output_port.direction = io.Direction.Output
        output_port.o = Signal(1)

        bidir_port = mock.MagicMock()
        bidir_port.direction = io.Direction.Bidir
        bidir_port.i = Signal(1)
        bidir_port.o = Signal(1)
        bidir_port.oe = Signal(1)

        platform._ports = {
            "input_port": input_port,
            "output_port": output_port,
            "bidir_port": bidir_port
        }

        # Create module with sync domain
        m = Module()
        m.domains += ClockDomain("sync")

        # Call _prepare
        result = platform._prepare(m)

        # Check that a design was returned
        self.assertIsNotNone(result)