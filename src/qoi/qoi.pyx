cimport qoi.qoi as qoi
import numpy as np
cimport numpy as np
from cpython.mem cimport PyMem_RawFree
import enum
from pathlib import Path

np.import_array()

ctypedef np.uint8_t DTYPE_t

class QOIColorSpace(enum.Enum):
    SRGB = qoi.QOI_SRGB
    LINEAR = qoi.QOI_LINEAR

cdef class PixelWrapper:
    cdef void* pixels

    cdef np.ndarray[DTYPE_t, ndim=3] as_ndarray(self, int height, int width, int channels, char * pixels):
        cdef np.npy_intp shape[3]
        cdef np.ndarray[DTYPE_t, ndim=3] ndarray
        self.pixels = pixels
        shape[:] = (height, width, channels)
        ndarray = np.PyArray_SimpleNewFromData(3, shape, np.NPY_UINT8, self.pixels)
        np.set_array_base(ndarray, self)
        return ndarray

    def __dealloc__(self):
        PyMem_RawFree(self.pixels)

cpdef int write(filename, unsigned char[:,:,::1] rgb, colorspace: QOIColorSpace = QOIColorSpace.SRGB) except? -1:
    cdef bytes filename_bytes 
    cdef const char* _filename
    cdef qoi.qoi_desc desc
    cdef int ret

    if not isinstance(colorspace, QOIColorSpace):
        raise ValueError("colorspace should be an instance of QOIColorSpace")
    if not isinstance(filename, (str, Path)):
        raise ValueError("filename should be a str or Path")

    filename_bytes = str(filename).encode('utf8')
    _filename = filename_bytes
    
    desc.height = <unsigned int>rgb.shape[0]
    desc.width = <unsigned int>rgb.shape[1]
    desc.channels = <unsigned char>rgb.shape[2]
    desc.colorspace = colorspace.value
    
    # if not rgb.flags['C_CONTIGUOUS']:
        # Makes a contiguous copy of the numpy array so we can process bytes directly:
        # rgb = np.ascontiguousarray(rgb)
    
    cdef int bytes_written
    with nogil:
        bytes_written = qoi.qoi_write(_filename, &rgb[0, 0, 0], &desc)
    if bytes_written == 0:
        raise RuntimeError("Failed to write!")
    return bytes_written

cpdef np.ndarray[DTYPE_t, ndim=3] read(filename, int channels = 0, unsigned char[::1] colorspace = bytearray(1)):
    # TODO: how to return desc.colorspace? A: How about return a tuple of ndarray and a wrapper around struct qoi_desc? or we can add another param like char[:] to simulate pointer
    cdef bytes filename_bytes
    cdef const char* _filename
    cdef qoi.qoi_desc desc
    cdef int ret
    cdef char* pixels

    if not isinstance(filename, (str, Path)):
        raise ValueError("filename should be a str or Path")

    filename_bytes = str(filename).encode('utf8')
    _filename = filename_bytes
    
    with nogil:
        pixels = <char *>qoi.qoi_read(_filename, &desc, channels)
    if pixels is NULL:
        raise RuntimeError("Failed to read!")
    try:
        colorspace[0] = desc.colorspace
        return PixelWrapper().as_ndarray(desc.height, desc.width, desc.channels if channels == 0 else channels, pixels)
    except:
        if pixels is not NULL:
            PyMem_RawFree(pixels)

cpdef bytes encode(unsigned char[:,:,::1] rgb, colorspace: QOIColorSpace = QOIColorSpace.SRGB):
    cdef qoi.qoi_desc desc
    cdef int ret, size
    cdef char * encoded

    if not isinstance(colorspace, QOIColorSpace):
        raise ValueError("colorspace should be an instance of QOIColorSpace")

    desc.height = <unsigned int>rgb.shape[0]
    desc.width = <unsigned int>rgb.shape[1]
    desc.channels = <unsigned char>rgb.shape[2]
    desc.colorspace = colorspace.value

    # if not rgb.flags['C_CONTIGUOUS']:
    #     rgb = np.ascontiguousarray(rgb) # makes a contiguous copy of the numpy array so we can read memory directly
    with nogil:
        encoded = <char *>qoi.qoi_encode(&rgb[0, 0, 0], &desc, &size)
    if encoded is NULL or size <= 0:
        raise RuntimeError("Failed to encode!")
    try:
        # TODO: does this create a copy? A: Yes, this equivalent to PyBytes_FromStringAndSize
        return encoded[:size] # :size is important here - tells cython about size, and handles null bytes
    finally:
        PyMem_RawFree(encoded)

cpdef np.ndarray[DTYPE_t, ndim=3] decode(const unsigned char[::1] data, int channels = 0, unsigned char[::1] colorspace = bytearray(1)):
    # TODO: what to do about desc.colorspace? A: How about return a tuple of ndarray and a wrapper around struct qoi_desc? or we can add another param like char[:] to simulate pointer
    cdef qoi.qoi_desc desc
    cdef int ret
    cdef char * pixels
    with nogil:
        pixels = <char *>qoi.qoi_decode(&data[0], <int>data.shape[0], &desc, channels)
    if pixels is NULL:
        raise RuntimeError("Failed to decode!")
    try:
        colorspace[0] = desc.colorspace
        return PixelWrapper().as_ndarray(desc.height, desc.width, desc.channels if channels == 0 else channels, pixels)
    except:
        if pixels is not NULL:
            PyMem_RawFree(pixels)
