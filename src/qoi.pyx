cimport qoi
import numpy as np
cimport numpy as np
from libc.stdlib cimport free
from cpython cimport PyObject, Py_INCREF
import enum
import warnings
from pathlib import Path

try:
    from _version import __version__
except:
    warnings.warn("Couldn't import _version.__version__ - please ensure you build in a way the utilises setuptools_scm")
    __version__ = None

np.import_array()


class QOIColorSpace(enum.Enum):
    SRGB = qoi.QOI_SRGB
    LINEAR = qoi.QOI_LINEAR

cdef class PixelWrapper:
    cdef void* pixels

    cdef as_ndarray(self, int height, int width, int channels, char * pixels):
        cdef np.npy_intp shape[3]
        cdef np.ndarray ndarray
        self.pixels = pixels
        shape[:] = (height, width, channels)
        ndarray = np.PyArray_SimpleNewFromData(3, shape, np.NPY_UINT8, self.pixels)
        ndarray.base = <PyObject*> self
        Py_INCREF(self)
        return ndarray

    def __dealloc__(self):
        free(self.pixels)

cpdef int write(filename, np.ndarray rgb, colorspace: QOIColorSpace = QOIColorSpace.SRGB) except? -1:
    cdef bytes filename_bytes 
    cdef char* _filename
    cdef qoi.qoi_desc desc
    cdef int ret

    if not isinstance(colorspace, QOIColorSpace):
        raise ValueError("colorspace should be an instance of QOIColorSpace")
    if not isinstance(filename, (str, Path)):
        raise ValueError("filename should be a str or Path")

    filename_bytes = str(filename).encode('utf8')
    _filename = filename_bytes
    
    desc.height = rgb.shape[0]
    desc.width = rgb.shape[1]
    desc.channels = rgb.shape[2]
    desc.colorspace = colorspace.value
    
    if not rgb.flags['C_CONTIGUOUS']:
        # Makes a contiguous copy of the numpy array so we can process bytes directly:
        rgb = np.ascontiguousarray(rgb)
    
    bytes_written = qoi.qoi_write(_filename, rgb.data, &desc)
    if bytes_written == 0:
        raise RuntimeError("Failed to write!")
    return bytes_written

cpdef np.ndarray read(filename, int channels = 0):
    # TODO: how to return desc.colorspace?
    cdef bytes filename_bytes
    cdef char* _filename
    cdef qoi.qoi_desc desc
    cdef int ret
    cdef char* pixels

    if not isinstance(filename, (str, Path)):
        raise ValueError("filename should be a str or Path")

    filename_bytes = str(filename).encode('utf8')
    _filename = filename_bytes
    

    pixels = <char *>qoi.qoi_read(_filename, &desc, channels)
    if pixels is NULL:
        raise RuntimeError("Failed to read!")
    try:
        return PixelWrapper().as_ndarray(desc.height, desc.width, desc.channels, pixels)
    except:
        if pixels is not NULL:
            free(pixels)

cpdef bytes encode(np.ndarray rgb, colorspace: QOIColorSpace = QOIColorSpace.SRGB):
    cdef qoi.qoi_desc desc
    cdef int ret, size
    cdef char * encoded

    if not isinstance(colorspace, QOIColorSpace):
        raise ValueError("colorspace should be an instance of QOIColorSpace")

    desc.height = rgb.shape[0]
    desc.width = rgb.shape[1]
    desc.channels = rgb.shape[2]
    desc.colorspace = colorspace.value

    if not rgb.flags['C_CONTIGUOUS']:
        rgb = np.ascontiguousarray(rgb) # makes a contiguous copy of the numpy array so we can read memory directly
    encoded = <char *>qoi.qoi_encode(rgb.data, &desc, &size)
    if encoded is NULL or size <= 0:
        raise RuntimeError("Failed to encode!")
    try:
        # TODO: does this create a copy?
        return encoded[:size] # :size is important here - tells cython about size, and handles null bytes
    finally:
        free(encoded)

cpdef np.ndarray decode(bytes data, int channels = 0):
    # TODO: what to do about desc.colorspace?
    cdef qoi.qoi_desc desc
    cdef int ret
    cdef char * pixels
    cdef char * cdata = data
    pixels = <char *>qoi.qoi_decode(&((<char *>data)[0]), len(data), &desc, channels)
    if pixels is NULL:
        raise RuntimeError("Failed to decode!")
    try:
        return PixelWrapper().as_ndarray(desc.height, desc.width, desc.channels, pixels)
    except:
        if pixels is not NULL:
            free(pixels)
