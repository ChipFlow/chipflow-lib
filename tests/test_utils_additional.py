# SPDX-License-Identifier: BSD-2-Clause
import unittest
from unittest import mock
import itertools
import logging
from pathlib import Path

from amaranth.lib import io
from pydantic import BaseModel

from chipflow_lib import ChipFlowError
from chipflow_lib.platforms.utils import (
    _chipflow_schema_uri, 
    _PinAnnotationModel,
    _PinAnnotation,
    PIN_ANNOTATION_SCHEMA,
    PinSignature,
    OutputPinSignature,
    InputPinSignature,
    BidirPinSignature,
    _Side,
    _group_consecutive_items,
    _find_contiguous_sequence,
    _BasePackageDef,
    _BareDiePackageDef,
    _QuadPackageDef,
    Package,
    Port,
    PortMap
)


class TestSchemaUtils(unittest.TestCase):
    def test_chipflow_schema_uri(self):
        """Test _chipflow_schema_uri function"""
        uri = _chipflow_schema_uri("test-schema", 1)
        self.assertEqual(uri, "https://api.chipflow.com/schemas/1/test-schema")

    def test_pin_annotation_model(self):
        """Test _PinAnnotationModel class"""
        # Test initialization
        model = _PinAnnotationModel(direction=io.Direction.Output, width=32, options={"opt1": "val1"})
        
        # Check properties
        self.assertEqual(model.direction, "o")
        self.assertEqual(model.width, 32)
        self.assertEqual(model.options, {"opt1": "val1"})
        
        # Test _annotation_schema class method
        schema = _PinAnnotationModel._annotation_schema()
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["$id"], PIN_ANNOTATION_SCHEMA)

    def test_pin_annotation(self):
        """Test _PinAnnotation class"""
        # Test initialization
        annotation = _PinAnnotation(direction=io.Direction.Input, width=16)
        
        # Check model
        self.assertEqual(annotation.model.direction, "i")
        self.assertEqual(annotation.model.width, 16)
        
        # Test origin property
        self.assertEqual(annotation.origin, annotation.model)
        
        # Test as_json method
        json_data = annotation.as_json()
        self.assertEqual(json_data["direction"], "i")
        self.assertEqual(json_data["width"], 16)
        self.assertEqual(json_data["options"], {})


class TestPortMap(unittest.TestCase):
    def test_portmap_creation(self):
        """Test creation of PortMap"""
        # Create port
        port1 = Port(type="input", pins=["1"], port_name="test_port", direction="i")
        port2 = Port(type="output", pins=["2"], port_name="port2", direction="o")
        
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
        port_map = PortMap(data)
        
        # Basic checks
        self.assertEqual(len(port_map), 1)
        self.assertIn("comp1", port_map)
        self.assertIn("iface1", port_map["comp1"])
        self.assertIn("port1", port_map["comp1"]["iface1"])
        self.assertEqual(port_map["comp1"]["iface1"]["port1"], port1)


class TestPackage(unittest.TestCase):
    def test_package_init(self):
        """Test Package initialization"""
        # Create package type
        package_type = _QuadPackageDef(name="test_package", width=10, height=10)
        
        # Create package
        package = Package(package_type=package_type)
        
        # Check properties
        self.assertEqual(package.package_type, package_type)
        self.assertEqual(package.power, {})
        self.assertEqual(package.clocks, {})
        self.assertEqual(package.resets, {})

    def test_package_add_pad(self):
        """Test Package.add_pad method"""
        # Create package type
        package_type = _QuadPackageDef(name="test_package", width=10, height=10)
        
        # Create package
        package = Package(package_type=package_type)
        
        # Add different pad types
        package.add_pad("clk1", {"type": "clock", "loc": "1"})
        package.add_pad("rst1", {"type": "reset", "loc": "2"})
        package.add_pad("vdd", {"type": "power", "loc": "3"})
        package.add_pad("gnd", {"type": "ground", "loc": "4"})
        package.add_pad("io1", {"type": "io", "loc": "5"})
        
        # Check that pads were added correctly
        self.assertIn("clk1", package.clocks)
        self.assertEqual(package.clocks["clk1"].pins, ["1"])
        
        self.assertIn("rst1", package.resets)
        self.assertEqual(package.resets["rst1"].pins, ["2"])
        
        self.assertIn("vdd", package.power)
        self.assertEqual(package.power["vdd"].pins, ["3"])
        
        self.assertIn("gnd", package.power)
        self.assertEqual(package.power["gnd"].pins, ["4"])
        
        # io pad should not be added to any of the special collections
        self.assertNotIn("io1", package.clocks)
        self.assertNotIn("io1", package.resets)
        self.assertNotIn("io1", package.power)


@mock.patch('chipflow_lib.platforms.utils.LockFile.model_validate_json')
@mock.patch('chipflow_lib.platforms.utils._ensure_chipflow_root')
@mock.patch('pathlib.Path.exists')
@mock.patch('pathlib.Path.read_text')
class TestLoadPinlock(unittest.TestCase):
    def test_load_pinlock_exists(self, mock_read_text, mock_exists, mock_ensure_chipflow_root, mock_validate_json):
        """Test load_pinlock when pins.lock exists"""
        # Import here to avoid issues during test collection
        from chipflow_lib.platforms.utils import load_pinlock
        
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
        from chipflow_lib.platforms.utils import load_pinlock
        
        # Setup mocks
        mock_ensure_chipflow_root.return_value = "/mock/chipflow/root"
        mock_exists.return_value = False
        
        # Call load_pinlock - should raise ChipFlowError
        with self.assertRaises(ChipFlowError) as cm:
            load_pinlock()
        
        # Check error message
        self.assertIn("Lockfile pins.lock not found", str(cm.exception))
        mock_ensure_chipflow_root.assert_called_once()
        mock_exists.assert_called_once()
        mock_read_text.assert_not_called()
        mock_validate_json.assert_not_called()