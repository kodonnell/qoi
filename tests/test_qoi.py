from pathlib import Path

import numpy as np
import pytest
import qoi

# Create an empty 3-channel image
RGB = np.random.randint(low=0, high=255, size=(224, 244, 3)).astype(np.uint8)
RGBA = np.random.randint(low=0, high=255, size=(224, 244, 4)).astype(np.uint8)


@pytest.mark.parametrize("is_path", [True, False])
@pytest.mark.parametrize("is_rgba", [True, False])
@pytest.mark.parametrize("colorspace", [qoi.QOIColorSpace.SRGB, qoi.QOIColorSpace.LINEAR, None])
def test_write_read(tmp_path: Path, is_path: bool, colorspace: qoi.QOIColorSpace, is_rgba: bool):
    tmp_path = str(tmp_path) + ".qoi"
    img = RGBA if is_rgba else RGB
    if is_path:
        tmp_path = Path(tmp_path)
    if colorspace is None:
        bytes_written = qoi.write(tmp_path, img)
    else:
        bytes_written = qoi.write(tmp_path, img, colorspace)
    assert bytes_written > 0
    img_read = qoi.read(tmp_path)
    assert np.array_equal(img, img_read)


@pytest.mark.parametrize("is_rgba", [True, False])
@pytest.mark.parametrize("colorspace", [qoi.QOIColorSpace.SRGB, qoi.QOIColorSpace.LINEAR, None])
def test_encode_decode(colorspace: qoi.QOIColorSpace, is_rgba: bool):
    img = RGBA if is_rgba else RGB
    if colorspace is None:
        bites = qoi.encode(img)
    else:
        bites = qoi.encode(img, colorspace)
    img_decoded = qoi.decode(bites)
    assert np.array_equal(img, img_decoded)


def test_version():
    assert qoi.__version__ is not None


@pytest.mark.xfail
def test_writes_without_extension(tmp_path):
    qoi.write(str(tmp_path), RGB, qoi.QOIColorSpace.SRGB)
