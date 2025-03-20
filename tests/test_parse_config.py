# SPDX-License-Identifier: BSD-2-Clause
import os
import unittest
from pathlib import Path

from chipflow_lib import _parse_config_file
from chipflow_lib.config_models import Config


class ParseConfigTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))
        current_dir = os.path.dirname(__file__)
        self.example_config = Path(os.environ["CHIPFLOW_ROOT"]) / "docs" / "example-chipflow.toml"
        self.mock_config = Path(current_dir) / "fixtures" / "mock.toml"

    def test_example_config_parsing(self):
        """Test that the example chipflow.toml can be parsed with our Pydantic models."""
        if self.example_config.exists():
            config_dict = _parse_config_file(self.example_config)
            self.assertIn("chipflow", config_dict)
            self.assertIn("silicon", config_dict["chipflow"])

            # Validate using Pydantic model
            config = Config.model_validate(config_dict)
            self.assertEqual(config.chipflow.project_name, "test-chip")
            self.assertEqual(config.chipflow.silicon.package, "pga144")
            self.assertEqual(str(config.chipflow.silicon.process), "gf130bcd")

    def test_mock_config_parsing(self):
        """Test that the mock chipflow.toml can be parsed with our Pydantic models."""
        if self.mock_config.exists():
            config_dict = _parse_config_file(self.mock_config)
            self.assertIn("chipflow", config_dict)
            self.assertIn("silicon", config_dict["chipflow"])

            # Validate using Pydantic model
            config = Config.model_validate(config_dict)
            self.assertEqual(config.chipflow.project_name, "proj-name")
            self.assertEqual(config.chipflow.silicon.package, "pga144")

            # Check that our model correctly handles the legacy format
            self.assertIn("sys_clk", config.chipflow.silicon.pads)
            self.assertEqual(config.chipflow.silicon.pads["sys_clk"].type, "clock")

            # Check power pins (should be auto-assigned type='power')
            self.assertIn("vss", config.chipflow.silicon.power)
            self.assertEqual(config.chipflow.silicon.power["vss"].type, "power")


if __name__ == "__main__":
    unittest.main()
