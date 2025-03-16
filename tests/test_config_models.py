# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest

from chipflow_lib.config_models import Config, PadConfig
from chipflow_lib.platforms.utils import Process


class ConfigModelsTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))

        # Create a valid config dict directly to test the model
        self.valid_config_dict = {
            "chipflow": {
                "project_name": "test-chip",
                "steps": {
                    "silicon": "chipflow_lib.steps.silicon:SiliconStep"
                },
                "top": {},
                "silicon": {
                    "process": "sky130",
                    "package": "cf20",
                    "pads": {
                        "sys_clk": {"type": "clock", "loc": "114"}
                    },
                    "power": {
                        "vdd": {"type": "power", "loc": "1"}
                    }
                }
            }
        }

    def test_config_validation(self):
        """Test that the Config model validates a known-good config."""
        config = Config.model_validate(self.valid_config_dict)
        self.assertEqual(config.chipflow.project_name, "test-chip")
        self.assertEqual(config.chipflow.silicon.package, "cf20")
        self.assertEqual(config.chipflow.silicon.process, Process.SKY130)

    def test_pad_config(self):
        """Test validation of pad configuration."""
        pad = PadConfig(type="clock", loc="114")
        self.assertEqual(pad.type, "clock")
        self.assertEqual(pad.loc, "114")

        # Test validation of loc format
        with self.assertRaises(ValueError):
            PadConfig(type="clock", loc="invalid-format")

    def test_nested_structure(self):
        """Test the nested structure of the Config model."""
        config = Config.model_validate(self.valid_config_dict)

        # Test silicon configuration
        silicon = config.chipflow.silicon
        self.assertEqual(silicon.package, "cf20")

        # Test pads
        self.assertEqual(len(silicon.pads), 1)
        pad = silicon.pads["sys_clk"]
        self.assertEqual(pad.type, "clock")
        self.assertEqual(pad.loc, "114")

        # Test power
        self.assertEqual(len(silicon.power), 1)
        power = silicon.power["vdd"]
        self.assertEqual(power.type, "power")
        self.assertEqual(power.loc, "1")
