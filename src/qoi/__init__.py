import enum

from qoi._qoi import __version__, decode, encode, read, write


class QOIColorSpace(enum.Enum):
    SRGB = 0
    LINEAR = 1


__all__ = ["QOIColorSpace", "__version__", "decode", "encode", "read", "write"]
