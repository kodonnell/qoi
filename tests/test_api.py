import numpy as np
import pytest
import qoi

RGB = np.random.randint(low=0, high=255, size=(64, 48, 3)).astype(np.uint8)
RGBA = np.random.randint(low=0, high=255, size=(64, 48, 4)).astype(np.uint8)


@pytest.mark.parametrize("wrap", [bytes, bytearray, memoryview, lambda b: np.frombuffer(b, np.uint8)])
def test_decode_accepts_buffers(wrap):
    assert np.array_equal(qoi.decode(wrap(qoi.encode(RGB))), RGB)


def test_decoded_array_is_a_normal_array():
    decoded = qoi.decode(qoi.encode(RGB))
    assert decoded.dtype == np.uint8
    assert decoded.shape == RGB.shape
    assert decoded.flags["C_CONTIGUOUS"] and decoded.flags["WRITEABLE"] and decoded.flags["OWNDATA"]
    decoded[0, 0, 0] += 1  # and is safe to modify


def test_decode_rgb_as_rgba():
    decoded = qoi.decode(qoi.encode(RGB), channels=4)
    assert decoded.shape == (*RGB.shape[:2], 4)
    assert np.array_equal(decoded[..., :3], RGB)
    assert (decoded[..., 3] == 255).all()


def test_decode_rgba_as_rgb():
    decoded = qoi.decode(qoi.encode(RGBA), channels=3)
    assert np.array_equal(decoded, RGBA[..., :3])


def test_read_channels_and_colorspace(tmp_path):
    path = tmp_path / "img.qoi"
    qoi.write(path, RGB, qoi.QOIColorSpace.LINEAR)
    cs = bytearray(1)
    decoded = qoi.read(str(path), channels=4, colorspace=cs)
    assert np.array_equal(decoded[..., :3], RGB)
    assert cs[0] == qoi.QOIColorSpace.LINEAR.value


def test_write_returns_file_size(tmp_path):
    path = tmp_path / "img.qoi"
    assert qoi.write(path, RGB) == path.stat().st_size == len(qoi.encode(RGB))


def test_colorspace_as_int():
    cs = bytearray(1)
    qoi.decode(qoi.encode(RGB, 1), colorspace=cs)
    assert cs[0] == 1


@pytest.mark.parametrize("colorspace", ["SRGB", 2, -1, 1.5])
def test_invalid_colorspace(colorspace):
    with pytest.raises(ValueError, match="colorspace"):
        qoi.encode(RGB, colorspace)


def test_readonly_colorspace_output():
    with pytest.raises(ValueError, match="colorspace"):
        qoi.decode(qoi.encode(RGB), colorspace=b"\x00")


def test_invalid_channels():
    with pytest.raises(ValueError, match="channels"):
        qoi.decode(qoi.encode(RGB), channels=2)


@pytest.mark.parametrize(
    "img",
    [
        RGB.astype(np.float32),  # wrong dtype
        RGB[..., 0],  # 2D
        RGB[..., :2].copy(),  # wrong number of channels
        RGB[:, ::2],  # not contiguous
        RGB.tolist(),  # not an array
    ],
)
def test_invalid_images(img):
    with pytest.raises(ValueError):
        qoi.encode(img)


def test_empty_image():
    with pytest.raises(RuntimeError, match="Failed to encode"):
        qoi.encode(np.zeros((0, 10, 3), np.uint8))


# Explicit ids, as otherwise pytest puts the whole bytes in the test id, which is too long for Windows.
@pytest.mark.parametrize(
    "data", [b"", b"not a qoi image", qoi.encode(RGB)[:-100]], ids=["empty", "not-qoi", "truncated"]
)
def test_invalid_data(data):
    with pytest.raises(RuntimeError, match="Failed to decode"):
        qoi.decode(data)


def test_read_missing_file(tmp_path):
    with pytest.raises(RuntimeError, match="Failed to read"):
        qoi.read(tmp_path / "nope.qoi")


def test_version_matches_metadata():
    from importlib.metadata import version

    assert qoi.__version__ == version("qoi")
