"""
Compatibility with the reference C implementation (https://github.com/phoboslab/qoi), which this package wrapped before
v0.8. The `*_ref.qoi` files in `tests/data` were written by that version, and the `.png` files hold the same pixels.
"""

from pathlib import Path

import numpy as np
import pytest
import qoi
from PIL import Image

DATA = Path(__file__).parent / "data"
CASES = [("koi_rgb", qoi.QOIColorSpace.SRGB), ("koi_rgba", qoi.QOIColorSpace.LINEAR)]


@pytest.mark.parametrize("name, colorspace", CASES)
def test_decodes_reference_encoder_output(name, colorspace):
    expected = np.asarray(Image.open(DATA / f"{name}.png"))
    cs = bytearray(1)
    decoded = qoi.read(DATA / f"{name}_ref.qoi", colorspace=cs)
    assert np.array_equal(decoded, expected)
    assert cs[0] == colorspace.value


@pytest.mark.parametrize("name, colorspace", CASES)
def test_encodes_same_header_as_reference(name, colorspace):
    img = np.asarray(Image.open(DATA / f"{name}.png"))
    ref = (DATA / f"{name}_ref.qoi").read_bytes()
    encoded = qoi.encode(img, colorspace)
    # The 14-byte header and 8-byte end marker are fully specified. The chunks in between can legitimately differ
    # between encoders (e.g. a run of one pixel vs an index lookup), so just check it round-trips.
    assert encoded[:14] == ref[:14]
    assert encoded[-8:] == ref[-8:]
    assert np.array_equal(qoi.decode(encoded), img)
