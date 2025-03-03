# SPDX-License-Identifier: BSD-2-Clause
import io
import json
import os
import tomli
import unittest
from contextlib import redirect_stdout
from pprint import pformat
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
            "id": "proj-name",
        }, 200)

    return MockResponse(None, 404)


class SiliconStepTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(current_dir)
        os.environ["CHIPFLOW_API_KEY_ID"] = "keyid"
        os.environ["CHIPFLOW_API_KEY_SECRET"] = "keysecret"

    @patch('dotenv.load_dotenv')
    @patch('requests.post', side_effect=mocked_requests_post)
    def test_submit_happy_path(self, mock_requests_post, mock_dotenv):
        customer_config = f"{current_dir}/fixtures/mock.toml"
        with open(customer_config, "rb") as f:
            config_dict = tomli.load(f)

        silicon_step = SiliconStep(config_dict)

        f = io.StringIO()
        with redirect_stdout(f):
            silicon_step.submit(current_dir + "/fixtures/mock.rtlil")
        output = f.getvalue()
        assert 'msg (#proj-name: name); https://example.com/build-url/' in output, "The printed output is correct."

        args = mock_requests_post.call_args_list[0][0]
        kwargs = mock_requests_post.call_args_list[0][1]
        data = kwargs["data"]
        files = kwargs["files"]
        config = json.loads(files["config"])
        rtlil = files["rtlil"].read()
        assert args[0] == 'https://app.chipflow-infra.com/api/builds'
        assert kwargs["auth"] == ("keyid", "keysecret")
        assert data["projectId"] == 'proj-name'
        assert isinstance(data["name"], str), "Name is a string"
        assert list(config["dependency_versions"]) == [
            "python",
            "yowasp-runtime", "yowasp-yosys",
            "amaranth", "amaranth-stdio", "amaranth-soc",
            "chipflow-lib",
            "amaranth-orchard", "amaranth-vexriscv",
        ], "We have entries for the the dependency versions"

        print(pformat(config))
        assert config["silicon"] == {
            'process': 'ihp_sg13g2',
            'pad_ring': 'pga144',
            'pads': {},
            'power': {
                'vss': {'loc': 'N1'},
                'vssio': {'loc': 'N5'},
                'vddio': {'loc': 'N6'},
                'vdd': {'loc': 'N7'}
            }
        }
        assert rtlil == b"fake-rtlil", "The RTL file was passed through."

        assert mock_dotenv.called
