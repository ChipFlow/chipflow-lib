# amaranth: UnusedElaboratable=no
# SPDX-License-Identifier: BSD-2-Clause

import os
import unittest

import tomli

from amaranth import *
from amaranth.hdl._ir import Design

from chipflow_lib import ChipFlowError
from chipflow_lib.platforms.silicon import SiliconPlatform


class SiliconPlatformTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))
        current_dir = os.path.dirname(__file__)
        customer_config = f"{current_dir}/fixtures/mock.toml"
        with open(customer_config, "rb") as f:
            self.config = tomli.load(f)

    def test_sync_domain_works(self):
        m = Module()
        m.domains += ClockDomain("sync")

        fragment = SiliconPlatform(self.config)._prepare(m)
        self.assertIsInstance(fragment, Design)

    def test_subfragment_works(self):
        m = Module()
        m.submodules += Module()

        fragment = SiliconPlatform(self.config)._prepare(m)
        self.assertIsInstance(fragment, Design)

    def test_wrong_clock_domain_name(self):
        m = Module()
        m.domains += ClockDomain("foo")

        with self.assertRaisesRegex(
                ChipFlowError,
                r"^Only a single clock domain, called 'sync', may be used: foo$"):
            SiliconPlatform(self.config).build(m)
