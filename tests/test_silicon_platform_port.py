# amaranth: UnusedElaboratable=no
# SPDX-License-Identifier: BSD-2-Clause
import unittest

from amaranth import Signal, Module
from amaranth.lib import wiring, io
from amaranth.lib.wiring import PureInterface

from chipflow_lib.platforms.silicon import SiliconPlatformPort
from chipflow_lib.platforms.utils import Port


class TestSiliconPlatformPort(unittest.TestCase):
    def test_init_input_port(self):
        # Test initialization with input direction
        port_obj = Port(type="input", pins=["1", "2", "3"], port_name="test_input",
                         direction="i", options={})
        spp = SiliconPlatformPort("comp", "test_input", port_obj)

        self.assertEqual(spp.direction, io.Direction.Input)
        self.assertEqual(len(spp), 3)  # Should match the port width
        self.assertFalse(spp.invert)

        # Test accessing properties
        _ = spp.i  # Should not raise an error
        with self.assertRaises(AttributeError):
            _ = spp.o  # Should raise an error for input port
        with self.assertRaises(AttributeError):
            _ = spp.oe  # Should raise an error for input port

    def test_init_output_port(self):
        # Test initialization with output direction
        port_obj = Port(type="output", pins=["1", "2"], port_name="test_output",
                         direction="o", options={})
        spp = SiliconPlatformPort("comp", "test_output", port_obj)

        self.assertEqual(spp.direction, io.Direction.Output)
        self.assertEqual(len(spp), 2)  # Should match the port width
        self.assertFalse(spp.invert)

        # Test accessing properties
        _ = spp.o  # Should not raise an error
        _ = spp.oe  # Should not raise an error since we now always have an _oe for outputs
        with self.assertRaises(AttributeError):
            _ = spp.i  # Should raise an error for output port

    def test_init_bidir_port(self):
        # Test initialization with bidirectional direction
        port_obj = Port(type="bidir", pins=["1", "2", "3", "4"], port_name="test_bidir",
                         direction="io", options={"all_have_oe": False})
        spp = SiliconPlatformPort("comp", "test_bidir", port_obj)

        self.assertEqual(spp.direction, io.Direction.Bidir)
        self.assertEqual(len(spp), 4)  # Should match the port width
        self.assertFalse(spp.invert)

        # Check the signals have the correct widths
        self.assertEqual(len(spp.i), 4)
        self.assertEqual(len(spp.o), 4)
        self.assertEqual(len(spp.oe), 1)  # Single OE for all pins

        # Test accessing properties
        _ = spp.i  # Should not raise an error
        _ = spp.o  # Should not raise an error
        _ = spp.oe  # Should not raise an error

    def test_init_bidir_port_all_have_oe(self):
        # Test initialization with bidirectional direction and all_have_oe=True
        port_obj = Port(type="bidir", pins=["1", "2", "3"], port_name="test_bidir",
                         direction="io", options={"all_have_oe": True})
        spp = SiliconPlatformPort("comp", "test_bidir", port_obj)

        self.assertEqual(spp.direction, io.Direction.Bidir)
        self.assertEqual(len(spp), 3)  # Should match the port width
        self.assertFalse(spp.invert)

        # Check the signals have the correct widths
        self.assertEqual(len(spp.i), 3)
        self.assertEqual(len(spp.o), 3)
        self.assertEqual(len(spp.oe), 3)  # One OE per pin

    def test_len_input_port(self):
        # Test __len__ with input direction
        port_obj = Port(type="input", pins=["1", "2", "3"], port_name="test_input",
                         direction="i", options={})
        spp = SiliconPlatformPort("comp", "test_input", port_obj)

        self.assertEqual(len(spp), 3)  # Should match the port width

    def test_len_output_port(self):
        # Test __len__ with output direction
        port_obj = Port(type="output", pins=["1", "2"], port_name="test_output",
                         direction="o", options={})
        spp = SiliconPlatformPort("comp", "test_output", port_obj)

        self.assertEqual(len(spp), 2)  # Should match the port width

    def test_len_bidir_port(self):
        # Test __len__ with bidirectional direction
        port_obj = Port(type="bidir", pins=["1", "2", "3", "4"], port_name="test_bidir",
                         direction="io", options={"all_have_oe": False})
        spp = SiliconPlatformPort("comp", "test_bidir", port_obj)

        self.assertEqual(len(spp), 4)  # Should match the port width

    def test_len_bidir_port_all_have_oe(self):
        # Test __len__ with bidirectional direction and all_have_oe=True
        port_obj = Port(type="bidir", pins=["1", "2", "3"], port_name="test_bidir",
                         direction="io", options={"all_have_oe": True})
        spp = SiliconPlatformPort("comp", "test_bidir", port_obj)

        self.assertEqual(len(spp), 3)  # Should match the port width

    def test_getitem(self):
        # Test __getitem__
        port_obj = Port(type="bidir", pins=["1", "2", "3"], port_name="test_bidir",
                         direction="io", options={"all_have_oe": True})
        spp = SiliconPlatformPort("comp", "test_bidir", port_obj)

        # Get a slice of the port
        slice_port = spp[1]
        self.assertEqual(spp.direction, slice_port.direction)
        self.assertEqual(spp.invert, slice_port.invert)

    def test_invert(self):
        # Test __invert__ for a bidirectional port since it has all signal types
        port_obj = Port(type="bidir", pins=["1", "2", "3"], port_name="test_bidir",
                         direction="io", options={"all_have_oe": True})
        spp = SiliconPlatformPort("comp", "test_bidir", port_obj)

        inverted_port = ~spp
        self.assertEqual(spp.direction, inverted_port.direction)
        self.assertNotEqual(spp.invert, inverted_port.invert)
        self.assertTrue(inverted_port.invert)

    def test_add(self):
        # Test __add__
        port_obj1 = Port(type="input", pins=["1", "2"], port_name="test_input1",
                          direction="i", options={})
        port_obj2 = Port(type="input", pins=["3", "4"], port_name="test_input2",
                          direction="i", options={})
        spp1 = SiliconPlatformPort("comp", "test_input1", port_obj1)
        spp2 = SiliconPlatformPort("comp", "test_input2", port_obj2)

        combined_port = spp1 + spp2
        self.assertEqual(spp1.direction, combined_port.direction)
        self.assertEqual(len(combined_port), len(spp1) + len(spp2))

    def test_wire_input(self):
        # Test wire method with a mock input interface
        port_obj = Port(type="input", pins=["1", "2", "3"], port_name="test_input",
                         direction="i", options={})
        spp = SiliconPlatformPort("comp", "test_input", port_obj)

        # Create a mock interface
        class MockSignature(wiring.Signature):
            def __init__(self):
                super().__init__({"i": wiring.In(3)})
                self._direction = io.Direction.Input

            @property
            def direction(self):
                return self._direction

        class MockInterface(PureInterface):
            def __init__(self):
                self.signature = MockSignature()
                self.i = Signal(3)

        interface = MockInterface()
        m = Module()

        # Wire should not raise an exception
        spp.wire(m, interface)

    def test_wire_output(self):
        # Test wire method with a mock output interface to cover line 105
        port_obj = Port(type="output", pins=["1", "2"], port_name="test_output",
                         direction="o", options={})
        spp = SiliconPlatformPort("comp", "test_output", port_obj)

        # Create a mock interface
        class MockSignature(wiring.Signature):
            def __init__(self):
                super().__init__({"o": wiring.Out(2)})
                self._direction = io.Direction.Output

            @property
            def direction(self):
                return self._direction

        class MockInterface(PureInterface):
            def __init__(self):
                self.signature = MockSignature()
                self.o = Signal(2)
                self.oe = Signal(1)

        interface = MockInterface()
        m = Module()

        # Wire should not raise an exception
        spp.wire(m, interface)

    def test_wire_bidir(self):
        # Test wire method with a mock bidirectional interface to cover both cases
        port_obj = Port(type="bidir", pins=["1", "2", "3"], port_name="test_bidir",
                         direction="io", options={"all_have_oe": True})
        spp = SiliconPlatformPort("comp", "test_bidir", port_obj)

        # Create a mock interface
        class MockSignature(wiring.Signature):
            def __init__(self):
                super().__init__({
                    "i": wiring.In(3),
                    "o": wiring.Out(3),
                    "oe": wiring.Out(3),
                })
                self._direction = io.Direction.Bidir

            @property
            def direction(self):
                return self._direction

        class MockInterface(PureInterface):
            def __init__(self):
                self.signature = MockSignature()
                self.i = Signal(3)
                self.o = Signal(3)
                self.oe = Signal(3)

        interface = MockInterface()
        m = Module()

        # Wire should not raise an exception
        spp.wire(m, interface)

    def test_repr(self):
        # Test the __repr__ method for a bidirectional port
        port_obj = Port(type="bidir", pins=["1", "2", "3"], port_name="test_bidir",
                         direction="io", options={"all_have_oe": True})
        spp = SiliconPlatformPort("comp", "test_bidir", port_obj)

        # Get the representation
        repr_str = repr(spp)

        # Check that it contains expected elements
        self.assertIn("SiliconPlatformPort", repr_str)
        self.assertIn("direction", repr_str)
        self.assertIn("width=3", repr_str)
        self.assertIn("invert=False", repr_str)