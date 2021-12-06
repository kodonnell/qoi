import numpy as np
import qoi

# Create an empty 3-channel image
rgb = np.random.randint(low=0, high=255, size=(224, 244, 3)).astype(np.uint8)


def test_write_read(tmp_path):
    tmp_path = str(tmp_path) + ".qoi"
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
