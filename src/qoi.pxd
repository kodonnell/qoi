cdef extern from "phoboslab_qoi/qoi.h":
    ctypedef struct qoi_desc:
        unsigned int width
        unsigned int height
        unsigned char channels
        unsigned char colorspace
    int qoi_write(const char *filename, const void *data, const qoi_desc *desc)
    void *qoi_read(const char *filename, qoi_desc *desc, int channels)
    void *qoi_encode(const void *data, const qoi_desc *desc, int *out_len)
    void *qoi_decode(const void *data, int size, qoi_desc *desc, int channels)
    int QOI_SRGB
    int QOI_LINEAR 