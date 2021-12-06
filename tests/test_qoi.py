from pathlib import Path

import numpy as np
import pytest
import qoi

# Create an empty 3-channel image
rgb = np.random.randint(low=0, high=255, size=(224, 244, 3)).astype(np.uint8)


@pytest.mark.parametrize("is_path", [True, False])
def test_write_read(tmp_path, is_path):
    tmp_path = str(tmp_path) + ".qoi"
    if is_path:
        tmp_path = Path(tmp_path)
    bytes_written = qoi.write(tmp_path, rgb, qoi.QOIColorSpace.SRGB)
    assert bytes_written > 0
    rgb_read = qoi.read(tmp_path)
    assert np.array_equal(rgb, rgb_read)


def test_encode_decode():
    bites = qoi.encode(rgb, qoi.QOIColorSpace.SRGB)
    rgb_decoded = qoi.decode(bites)
    assert np.array_equal(rgb, rgb_decoded)


def test_version():
    assert qoi.__version__ is not None


@pytest.mark.xfail
def test_writes_without_extension(tmp_path):
    qoi.write(str(tmp_path), rgb, qoi.QOIColorSpace.SRGB)
