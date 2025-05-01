# SPDX-License-Identifier: BSD-2-Clause
import itertools
import logging
import pytest #noqa 

from pprint import pformat

from amaranth.lib import io

from chipflow_lib.platforms.utils import IOSignature, OutputIOSignature, InputIOSignature, BidirIOSignature, _PinAnnotation, _PinAnnotationModel
from chipflow_lib.platforms.utils import PinList, _group_consecutive_items,_find_contiguous_sequence, _Side


logger = logging.getLogger(__name__)


def gen_quad_pins(width, height) -> PinList:
    return sorted(
            [e for e in itertools.product((_Side.N, _Side.S), range(width))] +
            [e for e in itertools.product((_Side.W, _Side.E), range(height))]
           )


def test_group_consecutive_items_null():
    ordering = gen_quad_pins(50,60)
    pins = ordering.copy()
    groups = _group_consecutive_items(pins,pins)
    assert len(groups.keys()) == 1
    assert len(ordering) in groups.keys()

def test_group_consecutive_items_nonconsecutive():
    ordering = gen_quad_pins(50,60)
    pins = ordering[0:6] + ordering[7:70] + ordering[71:180] + ordering[181:]
    logger.debug(f"{ordering} {pins}")
    groups = _group_consecutive_items(ordering,pins)
    logger.debug(f"\n{pformat(groups)}")
    assert len(ordering) == 50*2 + 60*2
    assert len(groups.keys()) == 4
    assert sum(groups.keys()) == len(ordering) - 3
    assert 6 in groups.keys()
    assert 70 - 7 in groups.keys()
    assert 180 - 71 in groups.keys()
    assert len(ordering) -181 in groups.keys()

def test_find_contiguous_sequence():
    ordering = gen_quad_pins(50,60)
    pins = ordering[0:6] + ordering[7:70] + ordering[71:180] + ordering[181:]
    seq = _find_contiguous_sequence(ordering, pins, 120)
    logger.debug(f"\n{pformat(seq)}")
    logger.debug(f"{ordering[71:180] + ordering[181:191]}")
    assert len(seq) == 120
    assert seq == ordering[71:180] + ordering[181:192]


def test_pin_signature():
    sig_bidir = IOSignature(io.Direction.Bidir, width=8)
    assert isinstance(sig_bidir, IOSignature)
    assert sig_bidir._direction == io.Direction.Bidir
    assert sig_bidir._width == 8
    assert "o" in sig_bidir.members
    assert "oe" in sig_bidir.members
    assert "i" in sig_bidir.members

    sig_output = OutputIOSignature(width=4)
    assert isinstance(sig_output, IOSignature)
    assert sig_output._direction == io.Direction.Output
    assert sig_output._width == 4
    assert "o" in sig_output.members
    assert "oe" not in sig_output.members
    assert "i" not in sig_output.members

    sig_input = InputIOSignature(width=2)
    assert isinstance(sig_input, IOSignature)
    assert sig_input._direction == io.Direction.Input
    assert sig_input._width == 2
    assert "o" not in sig_input.members
    assert "oe" not in sig_output.members
    assert "i" in sig_input.members

    sig_bidir_fn = BidirIOSignature(width=1)
    assert isinstance(sig_bidir_fn, IOSignature)
    assert sig_bidir_fn._direction == io.Direction.Bidir
    assert sig_bidir_fn._width == 1
    assert "o" in sig_bidir_fn.members
    assert "oe" in sig_bidir_fn.members
    assert "i" in sig_bidir_fn.members

def test_pin_annotation_model():
    model = _PinAnnotationModel(direction=io.Direction.Output, width=32)
    assert model.direction == "o"
    assert model.width == 32

def test_pin_annotation():
    annotation = _PinAnnotation(direction=io.Direction.Input, width=16)
    assert isinstance(annotation, _PinAnnotation)
    assert annotation.model.direction == "i"
    assert annotation.model.width == 16

def test_pin_annotation_as_json():
    annotation = _PinAnnotation(direction=io.Direction.Bidir, width=8)
    json_output = annotation.as_json()
    print(f"json_output: {json_output}") # Debug print using print()
    assert isinstance(json_output, dict)
    assert json_output["direction"] == "io"
    assert json_output["width"] == 8