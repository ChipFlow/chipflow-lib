# amaranth: UnusedElaboratable=no

# SPDX-License-Identifier: BSD-2-Clause
import unittest
from unittest import mock

from amaranth import Const
from amaranth.lib import io

from chipflow_lib import ChipFlowError
from chipflow_lib.platforms._utils import (
    IOSignature,
    IOModel,
    Package,
    Port,
    PortMap,
    PACKAGE_DEFINITIONS
)


class TestIOSignature(unittest.TestCase):
    def test_pin_signature_properties(self):
        """Test IOSignature properties"""
        # Create signature with options
        sig = IOSignature(direction=io.Direction.Bidir, width=4, all_have_oe=True, init=Const.cast(0))

        # Test properties
        self.assertEqual(sig.direction, io.Direction.Bidir)
        self.assertEqual(sig.width, 4)
        assert 'all_have_oe' in sig.options
        self.assertEqual(sig.options['all_have_oe'], True)

        # Test __repr__ - actual representation depends on Direction enum's representation
        repr_string = repr(sig)
        self.assertIn("IOSignature", repr_string)
        self.assertIn("4", repr_string)
        self.assertIn("all_have_oe=True", repr_string)
        self.assertIn("init=(const 1'd0)", repr_string)

    def test_pin_signature_annotations(self):
        """Test IOSignature annotations method"""
        # Create signature
        sig = IOSignature(direction=io.Direction.Output, width=8, init=Const.cast(42))

        # Create a mock object to pass to annotations
        mock_obj = object()

        # Get annotations with the mock object
        annotations = sig.annotations(mock_obj)

        # Should return a tuple with at least one annotation
        self.assertIsInstance(annotations, tuple)
        self.assertGreater(len(annotations), 0)

        # Find annotation with PIN_ANNOTATION_SCHEMA
        pin_annotation = None
        for annotation in annotations:
            if hasattr(annotation, 'as_json'):
                json_data = annotation.as_json()
                if json_data.get('width') == 8:
                    pin_annotation = annotation
                    break

        # Verify the annotation was found and has correct values
        self.assertIsNotNone(pin_annotation, "Pin annotation not found in annotations")
        assert pin_annotation is not None
        json_data = pin_annotation.as_json()
        self.assertEqual(json_data['direction'], 'o')
        self.assertEqual(json_data['width'], 8)
        self.assertEqual(json_data['init']['value'], 42)


class TestPortMap(unittest.TestCase):
    def test_portmap_creation(self):
        """Test creation of PortMap"""
        # Create port
        port1 = Port(type="input", pins=["1"], port_name="test_port", iomodel=IOModel(width=1, direction=io.Direction.Input))
        port2 = Port(type="output", pins=["2"], port_name="port2", iomodel=IOModel(width=1, direction=io.Direction.Output))

        # Create a dictionary with the right structure
        data = {
            "comp1": {
                "iface1": {
                    "port1": port1,
                    "port2": port2
                }
            }
        }

        # Create a PortMap
        port_map = PortMap(ports=data)

        # Basic checks
        self.assertEqual(len(port_map.ports), 1)
        self.assertIn("comp1", port_map.ports)
        self.assertIn("iface1", port_map.ports["comp1"])
        self.assertIn("port1", port_map.ports["comp1"]["iface1"])
        self.assertEqual(port_map.ports["comp1"]["iface1"]["port1"], port1)

    def test_portmap_mutable_mapping(self):
        """Test PortMap MutableMapping methods"""
        # Create an empty PortMap
        port_map = PortMap()

        # Test __setitem__ and __getitem__
        port_map.ports["comp1"] = {"iface1": {"port1": Port(type="input", pins=["1"], port_name="port1", iomodel=IOModel(width=1, direction=io.Direction.Input))}}
        self.assertIn("comp1", port_map.ports)
        self.assertEqual(port_map.ports["comp1"]["iface1"]["port1"].pins, ["1"])

        # Test __delitem__
        del port_map.ports["comp1"]
        self.assertNotIn("comp1", port_map.ports)

        # Test __iter__ and __len__
        port_map.ports["comp1"] = {"iface1": {}}
        port_map.ports["comp2"] = {"iface2": {}}
        self.assertEqual(len(port_map.ports), 2)
        self.assertEqual(set(port_map.ports), {"comp1", "comp2"})

    def test_portmap_methods(self):
        """Test PortMap helper methods"""
        # Create an empty PortMap
        port_map = PortMap()

        # Test _add_port with a new component and interface
        port1 = Port(type="input", pins=["1"], port_name="port1", iomodel=IOModel(width=1, direction=io.Direction.Input))
        port_map.add_port("comp1", "iface1", "port1", port1)

        self.assertIn("comp1", port_map.ports)
        self.assertIn("iface1", port_map.ports["comp1"])
        self.assertIn("port1", port_map.ports["comp1"]["iface1"])
        self.assertEqual(port_map.ports["comp1"]["iface1"]["port1"], port1)

        # Test _add_ports with a new interface
        ports = {
            "port2": Port(type="output", pins=["2"], port_name="port2", iomodel=IOModel(width=1, direction=io.Direction.Output)),
            "port3": Port(type="output", pins=["3"], port_name="port3", iomodel=IOModel(width=1, direction=io.Direction.Output))
        }
        port_map.add_ports("comp1", "iface2", ports)

        self.assertIn("iface2", port_map.ports["comp1"])
        self.assertEqual(len(port_map.ports["comp1"]["iface2"]), 2)
        self.assertEqual(port_map.ports["comp1"]["iface2"]["port2"].pins, ["2"])

        # Test get_ports
        result = port_map.get_ports("comp1", "iface1")
        self.assertEqual(result, {"port1": port1})

        # Test get_ports with non-existent component
        with self.assertRaises(KeyError):
            result = port_map.get_ports("non_existent", "iface1")


class TestPackageDefinitions(unittest.TestCase):
    def test_package_definitions_exist(self):
        """Test that standard package definitions exist"""
        self.assertIn("cf20", PACKAGE_DEFINITIONS)

        # Test CF20 package definition
        cf20_pkg = PACKAGE_DEFINITIONS["cf20"]
        self.assertEqual(cf20_pkg.name, "cf20")
        self.assertEqual(cf20_pkg.width, 7)
        self.assertEqual(cf20_pkg.height, 3)
        self.assertEqual(cf20_pkg.package_type, "BareDiePackageDef")


class TestPackage(unittest.TestCase):
    def test_package_init(self):
        """Test Package initialization"""
        # Get package type from definitions
        package_type = PACKAGE_DEFINITIONS["cf20"]

        # Create package
        package = Package(type=package_type)

        # Check properties
        self.assertEqual(package.type, package_type)
        self.assertEqual(package.type.name, "cf20")


class TestPort(unittest.TestCase):
    def test_port_width(self):
        """Test Port.width property"""
        # Create port with multiple pins
        port = Port(type="test", pins=["1", "2", "3"], port_name="test_port", iomodel=IOModel(width=3, direction=io.Direction.Input))

        # Check width
        self.assertEqual(port.width, 3)

        # Test port with no pins
        port_no_pins = Port(type="test", pins=None, port_name="test_port", iomodel=IOModel(width=0, direction=io.Direction.Input))
        # When pins=None, width property should fail since it can't verify consistency
        with self.assertRaises(AssertionError):
            _ = port_no_pins.width


@mock.patch('chipflow_lib.platforms._utils.LockFile.model_validate_json')
@mock.patch('chipflow_lib.platforms._utils._ensure_chipflow_root')
@mock.patch('pathlib.Path.exists')
@mock.patch('pathlib.Path.read_text')
class TestLoadPinlock(unittest.TestCase):
    def test_load_pinlock_exists(self, mock_read_text, mock_exists, mock_ensure_chipflow_root, mock_validate_json):
        """Test load_pinlock when pins.lock exists"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms._utils import load_pinlock

        # Setup mocks
        mock_ensure_chipflow_root.return_value = "/mock/chipflow/root"
        mock_exists.return_value = True
        mock_read_text.return_value = '{"json": "content"}'
        mock_validate_json.return_value = "parsed_lock_file"

        # Call load_pinlock
        result = load_pinlock()

        # Check results
        self.assertEqual(result, "parsed_lock_file")
        mock_ensure_chipflow_root.assert_called_once()
        mock_exists.assert_called_once()
        mock_read_text.assert_called_once()
        mock_validate_json.assert_called_once_with('{"json": "content"}')

    def test_load_pinlock_not_exists(self, mock_read_text, mock_exists, mock_ensure_chipflow_root, mock_validate_json):
        """Test load_pinlock when pins.lock doesn't exist"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms._utils import load_pinlock

        # Setup mocks
        mock_ensure_chipflow_root.return_value = "/mock/chipflow/root"
        mock_exists.return_value = False

        # Call load_pinlock - should raise ChipFlowError
        with self.assertRaises(ChipFlowError) as cm:
            load_pinlock()

        # Check error message
        self.assertIn("Lockfile `pins.lock` not found", str(cm.exception))
        mock_ensure_chipflow_root.assert_called_once()
        mock_exists.assert_called_once()
        mock_read_text.assert_not_called()
        mock_validate_json.assert_not_called()
