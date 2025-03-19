# SPDX-License-Identifier: BSD-2-Clause
import os
import pytest
import unittest
from unittest import mock
from pathlib import Path

import tomli

from chipflow_lib.config_models import SiliconConfig, PadConfig, Config, ChipFlowConfig, StepsConfig
from chipflow_lib.platforms.utils import LockFile, Process, Port
from chipflow_lib.pin_lock import lock_pins


class TestPinLock(unittest.TestCase):
    def setUp(self):
        # Set up environment variables and paths for testing
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))
        self.current_dir = os.path.dirname(__file__)
        # Load configuration for tests
        self.config_path = f"{self.current_dir}/fixtures/mock.toml"
        with open(self.config_path, "rb") as f:
            self.config = tomli.load(f)

    def test_config_model_structure(self):
        """Test that our Pydantic models correctly represent the TOML structure."""
        # Create a PadConfig instance
        pad = PadConfig(type="io", loc="N1")
        self.assertEqual(pad.type, "io")
        self.assertEqual(pad.loc, "N1")
        
        # Create a SiliconConfig instance
        silicon = SiliconConfig(
            process=Process.IHP_SG13G2,
            package="cf20",
            pads={"test_pad": pad},
            power={"vdd": PadConfig(type="power", loc="1")}
        )
        self.assertEqual(silicon.process, Process.IHP_SG13G2)
        self.assertEqual(silicon.package, "cf20")
        self.assertEqual(silicon.pads["test_pad"].type, "io")
        self.assertEqual(silicon.power["vdd"].type, "power")
        
        # Create a StepsConfig instance
        steps = StepsConfig(silicon="chipflow_lib.steps.silicon:SiliconStep")
        self.assertEqual(steps.silicon, "chipflow_lib.steps.silicon:SiliconStep")
        
        # Create a ChipFlowConfig instance
        chipflow_config = ChipFlowConfig(
            project_name="test",
            top={"test_component": "test.module:TestComponent"},
            steps=steps,
            silicon=silicon
        )
        self.assertEqual(chipflow_config.project_name, "test")
        
        # Create a full Config instance
        config = Config(chipflow=chipflow_config)
        self.assertEqual(config.chipflow.project_name, "test")
        self.assertEqual(config.chipflow.silicon.process, Process.IHP_SG13G2)
    
    def test_validate_real_config(self):
        """Test that our Mock TOML file passes validation."""
        # Convert the TOML dict to a Config model
        config = Config.model_validate(self.config)
        
        # Verify basic fields
        self.assertEqual(config.chipflow.project_name, "proj-name")
        self.assertEqual(config.chipflow.steps.silicon, "chipflow_lib.steps.silicon:SiliconStep")
        self.assertEqual(config.chipflow.silicon.process, Process.IHP_SG13G2)
        self.assertEqual(config.chipflow.silicon.package, "pga144")
        
        # Verify clocks and resets
        self.assertEqual(config.chipflow.clocks["default"], "sys_clk")
        self.assertEqual(config.chipflow.resets["default"], "sys_rst_n")
        
        # Verify pads
        self.assertEqual(config.chipflow.silicon.pads["sys_clk"].type, "clock")  # clk gets mapped to clock
        self.assertEqual(config.chipflow.silicon.pads["sys_clk"].loc, "N3")
        self.assertEqual(config.chipflow.silicon.pads["sys_rst_n"].type, "i")
        
        # Verify power pads
        self.assertEqual(config.chipflow.silicon.power["vss"].type, "power")  # Inferred from section
        self.assertEqual(config.chipflow.silicon.power["vss"].loc, "N1")
    
    def test_pydantic_lockfile_creation(self):
        """Test creating a lock file using the real Pydantic models"""
        # Create a new silicon configuration with proper process and package
        silicon_config = SiliconConfig(
            process=Process.IHP_SG13G2,
            package="cf20",
            pads={"clock": PadConfig(type="clock", loc="1")},
            power={"vdd": PadConfig(type="power", loc="3")}
        )
        
        # Create the steps config
        steps_config = StepsConfig(silicon="chipflow_lib.steps.silicon:SiliconStep")
        
        # Create a full chipflow config
        chipflow_config = ChipFlowConfig(
            project_name="test_project",
            top={"mock_component": "module.MockComponent"},
            steps=steps_config,
            silicon=silicon_config
        )
        
        # Create the complete config
        config = Config(chipflow=chipflow_config)
        
        # Create a new lock file with the config
        lock_file = LockFile(package="cf20")
        
        # Add a port to the lock file
        lock_file.add_port("comp1", "if1", "port1", "o", "5")
        
        # Verify port was added correctly
        port = lock_file.port_map["comp1"]["if1"]["port1"]
        self.assertEqual(port.port_name, "port1")
        self.assertEqual(port.port_type, "o")
        self.assertEqual(port.pin, "5")
        
        # Test serialization
        json_data = lock_file.model_dump_json(indent=2)
        self.assertIn('"package": "cf20"', json_data)
        self.assertIn('"port_name": "port1"', json_data)
        self.assertIn('"pin": "5"', json_data)
        
        # Test deserialization
        loaded_lock = LockFile.model_validate_json(json_data)
        self.assertEqual(loaded_lock.package, lock_file.package)
        self.assertEqual(loaded_lock.port_map["comp1"]["if1"]["port1"].pin, "5")


class TestProcessorConfig(unittest.TestCase):
    """Test cases for Process enum"""
    
    def test_process_enum_values(self):
        """Test Process enum has expected values"""
        # Check enum values match expected values
        self.assertEqual(Process.SKY130, "sky130")
        self.assertEqual(Process.GF180, "gf180")
        self.assertEqual(Process.HELVELLYN2, "helvellyn2")
        self.assertEqual(Process.GF130BCD, "gf130bcd")
        self.assertEqual(Process.IHP_SG13G2, "ihp_sg13g2")
        
        # Test that we can create a SiliconConfig with a valid process
        config = SiliconConfig(
            process=Process.IHP_SG13G2,
            package="cf20"
        )
        self.assertEqual(config.process, Process.IHP_SG13G2)
        
        # Test JSON serialization
        json_str = config.model_dump_json()
        self.assertIn('"process": "ihp_sg13g2"', json_str)


class TestPadConfig(unittest.TestCase):
    """Test cases for PadConfig model"""
    
    def test_pad_config_validation(self):
        """Test pad config validation rules"""
        # Valid pad configs
        valid_pads = [
            {"type": "io", "loc": "1"},
            {"type": "i", "loc": "N2"},
            {"type": "o", "loc": "E3"},
            {"type": "clock", "loc": "W4"},
            {"type": "reset", "loc": "S5"},
            {"type": "power", "loc": "6"},
            {"type": "ground", "loc": "7"}
        ]
        
        for pad_dict in valid_pads:
            # Should not raise validation error
            pad = PadConfig(**pad_dict)
            self.assertEqual(pad.type, pad_dict["type"])
            self.assertEqual(pad.loc, pad_dict["loc"])
        
        # Invalid type
        with self.assertRaises(ValueError):
            PadConfig(type="invalid", loc="1")
        
        # Invalid location format
        with self.assertRaises(ValueError):
            PadConfig(type="io", loc="invalid")
        
        # Test clk to clock mapping
        pad_dict = {"type": "clk", "loc": "1"}
        pad = PadConfig.validate_pad_dict(pad_dict, mock.MagicMock())
        self.assertEqual(pad["type"], "clock")


@mock.patch("chipflow_lib.pin_lock.top_interfaces")
class TestPortIntegration(unittest.TestCase):
    """Test integration between Port and LockFile"""
    
    def test_port_in_lockfile(self, mock_top_interfaces):
        """Test that a Port can be added to LockFile correctly"""
        # Create a Port
        port = Port(
            type="output",
            pins=["1"],
            port_name="test_port",
            direction="o",
            options={}
        )
        
        # Verify Port attributes
        self.assertEqual(port.type, "output")
        self.assertEqual(port.pins, ["1"])
        self.assertEqual(port.port_name, "test_port")
        self.assertEqual(port.direction, "o")
        
        # Create a LockFile
        lock_file = LockFile(package="cf20")
        
        # Add the port to the lock file
        lock_file.add_port("comp1", "if1", port.port_name, port.direction, port.pins[0])
        
        # Verify port was added correctly
        self.assertIn("comp1", lock_file.port_map)
        self.assertIn("if1", lock_file.port_map["comp1"])
        self.assertIn(port.port_name, lock_file.port_map["comp1"]["if1"])
        
        added_port = lock_file.port_map["comp1"]["if1"][port.port_name]
        self.assertEqual(added_port.port_name, port.port_name)
        self.assertEqual(added_port.port_type, port.direction)
        self.assertEqual(added_port.pin, port.pins[0])
