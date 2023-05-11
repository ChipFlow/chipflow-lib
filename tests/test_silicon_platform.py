# amaranth: UnusedElaboratable=no
# SPDX-License-Identifier: BSD-2-Clause

import os

import unittest
from amaranth import *
from amaranth.hdl.ir import Fragment

from chipflow_lib import ChipFlowError
from chipflow_lib.platforms.silicon import SiliconPlatform


class SiliconPlatformTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["CHIPFLOW_ROOT"] = os.path.dirname(os.path.dirname(__file__))

    def test_sync_domain_works(self):
        m = Module()
        m.domains += ClockDomain("sync")

        fragment = SiliconPlatform(pads={})._prepare(m)
        self.assertIsInstance(fragment, Fragment)

    def test_subfragment_works(self):
        m = Module()
        m.submodules += Module()

        fragment = SiliconPlatform(pads={})._prepare(m)
        self.assertIsInstance(fragment, Fragment)

    def test_wrong_clock_domain_name(self):
        m = Module()
        m.domains += ClockDomain("foo")

        with self.assertRaisesRegex(
                ChipFlowError,
                r"^Only a single clock domain, called 'sync', may be used$"):
            SiliconPlatform(pads={}).build(m)
