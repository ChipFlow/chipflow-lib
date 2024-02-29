# SPDX-License-Identifier: BSD-2-Clause

import io
import json
import os
import tomli
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from chipflow_lib.steps.silicon import SiliconStep


current_dir = os.path.dirname(__file__)


def mocked_requests_post(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    if args[0] == 'https://app.chipflow-infra.com/api/builds':
        return MockResponse({
            "ok": True,
            "msg": "msg",
            "url": "https://example.com/build-url/",
            "name": "name",
            "id": 123,
        }, 200)

    return MockResponse(None, 404)


class SiliconStepTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(current_dir)
        os.environ["CHIPFLOW_API_KEY_ID"] = "keyid"
        os.environ["CHIPFLOW_API_KEY_SECRET"] = "keysecret"

    @patch('requests.post', side_effect=mocked_requests_post)
    def test_submit_happy_path(self, mock_requests_post):
        customer_config = f"{current_dir}/fixtures/chipflow-flexic.toml"
        with open(customer_config, "rb") as f:
            config_dict = tomli.load(f)

        silicon_step = SiliconStep(config_dict)

        f = io.StringIO()
        with redirect_stdout(f):
            silicon_step.submit(current_dir + "/fixtures/mock.rtlil")
        output = f.getvalue()
        assert 'msg (#123: name); https://example.com/build-url/' in output, "The printed output is correct."

        args = mock_requests_post.call_args_list[0][0]
        kwargs = mock_requests_post.call_args_list[0][1]
        data = kwargs["data"]
        files = kwargs["files"]
        config = json.loads(files["config"])
        rtlil = files["rtlil"].read()
        assert args[0] == 'https://app.chipflow-infra.com/api/builds'
        assert kwargs["auth"] == ("keyid", "keysecret")
        assert data["projectId"] == 123
        assert isinstance(data["name"], str), "Name is a string"
        assert list(config["dependency_versions"]) == [
            "python",
            "yowasp-runtime", "yowasp-yosys",
            "amaranth", "amaranth-stdio", "amaranth-soc",
            "chipflow-lib",
            "amaranth-orchard", "amaranth-vexriscv",
        ], "We have entries for the the dependency versions"

        assert config["silicon"] == {
            'process': 'customer1',
            'pad_ring':
            'cf20',
            'pads': {},
            'power': {
                'vss': {'loc': 'N1'},
                'vssio': {'loc': 'N5'},
                'vddio': {'loc': 'N6'},
                'vdd': {'loc': 'N7'}
            }
        }
        assert rtlil == b"fake-rtlil", "The RTL file was passed through."
