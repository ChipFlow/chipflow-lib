# SPDX-License-Identifier: BSD-2-Clause
import logging
import pytest  #noqa

from amaranth import Const
from amaranth.lib import io

from chipflow_lib.platforms._utils import IOSignature, OutputIOSignature, InputIOSignature, BidirIOSignature


logger = logging.getLogger(__name__)


def test_pin_signature():
    sig_bidir = IOSignature(direction=io.Direction.Bidir, width=8)
    assert isinstance(sig_bidir, IOSignature)
    assert sig_bidir.direction == io.Direction.Bidir
    assert sig_bidir.width == 8
    assert "o" in sig_bidir.members
    assert "oe" in sig_bidir.members
    assert "i" in sig_bidir.members

    sig_output = OutputIOSignature(width=4)
    assert isinstance(sig_output, IOSignature)
    assert sig_output.direction == io.Direction.Output
    assert sig_output.width == 4
    assert "o" in sig_output.members
    assert "oe" not in sig_output.members
    assert "i" not in sig_output.members

    sig_input = InputIOSignature(width=2)
    assert isinstance(sig_input, IOSignature)
    assert sig_input.direction == io.Direction.Input
    assert sig_input.width == 2
    assert "o" not in sig_input.members
    assert "oe" not in sig_input.members
    assert "i" in sig_input.members

    sig_bidir_fn = BidirIOSignature(width=1)
    assert isinstance(sig_bidir_fn, IOSignature)
    assert sig_bidir_fn.direction == io.Direction.Bidir
    assert sig_bidir_fn.width == 1
    assert "o" in sig_bidir_fn.members
    assert "oe" in sig_bidir_fn.members
    assert "i" in sig_bidir_fn.members


def test_pin_signature_annotations():
    """Test IOSignature annotations functionality"""
    sig = IOSignature(direction=io.Direction.Input, width=16)

    # Create a mock object to pass to annotations
    mock_obj = object()

    # Get annotations
    annotations = sig.annotations(mock_obj)
    assert isinstance(annotations, tuple)
    assert len(annotations) > 0

    # Find the pin annotation
    pin_annotation = None
    for annotation in annotations:
        if hasattr(annotation, 'as_json'):
            json_data = annotation.as_json()
            if json_data.get('width') == 16:
                pin_annotation = annotation
                break

    assert pin_annotation is not None
    json_data = pin_annotation.as_json()
    assert json_data["direction"] == 'i'
    assert json_data["width"] == 16


def test_signature_factory_functions():
    """Test the factory functions for creating IOSignatures"""

    # Test OutputIOSignature factory
    output_sig = OutputIOSignature(width=32, init=Const.cast(0x12345678))
    assert output_sig.direction == io.Direction.Output
    assert output_sig.width == 32

    # Test InputIOSignature factory
    input_sig = InputIOSignature(width=16)
    assert input_sig.direction == io.Direction.Input
    assert input_sig.width == 16

    # Test BidirIOSignature factory
    bidir_sig = BidirIOSignature(width=8, all_have_oe=True)
    assert bidir_sig.direction == io.Direction.Bidir
    assert bidir_sig.width == 8
