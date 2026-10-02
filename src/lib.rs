//! Python bindings for the `qoi` crate.
//!
//! Performance notes:
//! - All encoding/decoding and file IO happens with the GIL released (`py.detach`), so it runs in parallel across
//!   threads. The module is also declared safe for free-threaded Python (`gil_used = false`).
//! - No unnecessary copies: `encode`/`write` read the numpy array's memory in place, and `decode`/`read` decode
//!   straight into a newly allocated numpy array. (`encode` does copy once, into the returned `bytes`.)

use std::path::PathBuf;

use numpy::{PyArray3, PyArrayMethods, PyUntypedArrayMethods};
use pyo3::buffer::PyBuffer;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use qoi::{Channels, ColorSpace, Decoder, Encoder};

fn parse_colorspace(colorspace: Option<&Bound<'_, PyAny>>) -> PyResult<ColorSpace> {
    let Some(cs) = colorspace else {
        return Ok(ColorSpace::Srgb);
    };
    // Normally a QOIColorSpace (a Python enum, so use its .value), but a plain int is fine too.
    let value = cs.getattr(intern!(cs.py(), "value")).unwrap_or_else(|_| cs.clone());
    value
        .extract::<u8>()
        .ok()
        .and_then(|v| ColorSpace::try_from(v).ok())
        .ok_or_else(|| PyValueError::new_err("colorspace should be an instance of QOIColorSpace"))
}

fn parse_channels(channels: u8) -> PyResult<Option<Channels>> {
    match channels {
        0 => Ok(None),
        3 => Ok(Some(Channels::Rgb)),
        4 => Ok(Some(Channels::Rgba)),
        _ => Err(PyValueError::new_err(
            "channels should be 0 (as stored in the image), 3 or 4",
        )),
    }
}

/// Check an optional colorspace output buffer (e.g. a `bytearray(1)`) can be written to.
fn check_colorspace_out(out: Option<&PyBuffer<u8>>) -> PyResult<()> {
    match out {
        Some(buf) if buf.readonly() || buf.item_count() < 1 => Err(PyValueError::new_err(
            "colorspace should be a writable buffer of at least one byte, e.g. bytearray(1)",
        )),
        _ => Ok(()),
    }
}

fn encode_array(py: Python<'_>, rgb: &Bound<'_, PyAny>, colorspace: Option<&Bound<'_, PyAny>>) -> PyResult<Vec<u8>> {
    let colorspace = parse_colorspace(colorspace)?;
    let array = rgb
        .cast::<PyArray3<u8>>()
        .map_err(|_| PyValueError::new_err("expected a uint8 numpy array with shape (height, width, channels)"))?;
    let array = array.try_readonly().map_err(|e| PyValueError::new_err(e.to_string()))?;
    let &[height, width, channels] = array.shape() else {
        unreachable!("PyArray3 is always 3D")
    };
    if channels != 3 && channels != 4 {
        return Err(PyValueError::new_err(format!(
            "expected 3 or 4 channels, got {channels}"
        )));
    }
    let (Ok(width), Ok(height)) = (u32::try_from(width), u32::try_from(height)) else {
        return Err(PyValueError::new_err("image is too large"));
    };
    // Borrow the array's memory directly - no copy.
    let pixels = array
        .as_slice()
        .map_err(|_| PyValueError::new_err("array should be C-contiguous (see numpy.ascontiguousarray)"))?;
    py.detach(|| {
        Encoder::new(pixels, width, height)?
            .with_colorspace(colorspace)
            .encode_to_vec()
    })
    .map_err(|e| PyRuntimeError::new_err(format!("Failed to encode! {e}")))
}

fn decode_bytes<'py>(
    py: Python<'py>,
    data: &[u8],
    channels: u8,
    colorspace: Option<&PyBuffer<u8>>,
) -> PyResult<Bound<'py, PyArray3<u8>>> {
    let fail = |e: qoi::Error| PyRuntimeError::new_err(format!("Failed to decode! {e}"));
    let mut decoder = Decoder::new(data).map_err(fail)?;
    if let Some(channels) = parse_channels(channels)? {
        decoder = decoder.with_channels(channels);
    }
    let header = *decoder.header();
    let shape = [
        header.height as usize,
        header.width as usize,
        decoder.channels().as_u8() as usize,
    ];
    // SAFETY: the array is left uninitialised, but every byte is written by `decode_to_buf` before it's returned, and
    // it's not visible to any other code until then.
    let array = unsafe { PyArray3::<u8>::new(py, shape, false) };
    let out = unsafe { array.as_slice_mut() }.expect("new arrays are C-contiguous");
    py.detach(|| decoder.decode_to_buf(out)).map_err(fail)?;
    if let Some(buf) = colorspace {
        // SAFETY: check_colorspace_out confirmed it's writable and non-empty, and `buf` keeps the memory alive.
        unsafe { *buf.buf_ptr().cast::<u8>() = header.colorspace.into() };
    }
    Ok(array)
}

/// Encode a (height, width, channels) uint8 numpy array (channels = 3 or 4) to QOI bytes.
#[pyfunction]
#[pyo3(signature = (rgb, colorspace=None))]
fn encode<'py>(
    py: Python<'py>,
    rgb: &Bound<'py, PyAny>,
    colorspace: Option<&Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyBytes>> {
    let encoded = encode_array(py, rgb, colorspace)?;
    Ok(PyBytes::new(py, &encoded))
}

/// Decode QOI bytes (or any contiguous buffer) to a (height, width, channels) uint8 numpy array.
///
/// `channels` forces 3 or 4 output channels (0 means use what's stored in the image). If `colorspace` is a writable
/// buffer (e.g. `bytearray(1)`), the image's colorspace is written to its first byte.
#[pyfunction]
#[pyo3(signature = (data, channels=0, colorspace=None))]
fn decode<'py>(
    py: Python<'py>,
    data: PyBuffer<u8>,
    channels: u8,
    colorspace: Option<PyBuffer<u8>>,
) -> PyResult<Bound<'py, PyArray3<u8>>> {
    check_colorspace_out(colorspace.as_ref())?;
    if !data.is_c_contiguous() {
        return Err(PyValueError::new_err("data should be a contiguous buffer"));
    }
    // SAFETY: contiguous, and `data` keeps the exporting object (and its memory) alive and locked until it's dropped.
    let bytes = unsafe { std::slice::from_raw_parts(data.buf_ptr().cast::<u8>(), data.len_bytes()) };
    decode_bytes(py, bytes, channels, colorspace.as_ref())
}

/// Encode a (height, width, channels) uint8 numpy array and write it to a file. Returns the number of bytes written.
#[pyfunction]
#[pyo3(signature = (filename, rgb, colorspace=None))]
fn write<'py>(
    py: Python<'py>,
    filename: PathBuf,
    rgb: &Bound<'py, PyAny>,
    colorspace: Option<&Bound<'py, PyAny>>,
) -> PyResult<usize> {
    let encoded = encode_array(py, rgb, colorspace)?;
    py.detach(|| std::fs::write(&filename, &encoded))
        .map_err(|e| PyRuntimeError::new_err(format!("Failed to write {}! {e}", filename.display())))?;
    Ok(encoded.len())
}

/// Read and decode a QOI file to a (height, width, channels) uint8 numpy array. See `decode` for the other arguments.
#[pyfunction]
#[pyo3(signature = (filename, channels=0, colorspace=None))]
fn read<'py>(
    py: Python<'py>,
    filename: PathBuf,
    channels: u8,
    colorspace: Option<PyBuffer<u8>>,
) -> PyResult<Bound<'py, PyArray3<u8>>> {
    check_colorspace_out(colorspace.as_ref())?;
    let data = py
        .detach(|| std::fs::read(&filename))
        .map_err(|e| PyRuntimeError::new_err(format!("Failed to read {}! {e}", filename.display())))?;
    decode_bytes(py, &data, channels, colorspace.as_ref())
}

#[pymodule(gil_used = false)]
fn _qoi(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(encode, m)?)?;
    m.add_function(wrap_pyfunction!(decode, m)?)?;
    m.add_function(wrap_pyfunction!(write, m)?)?;
    m.add_function(wrap_pyfunction!(read, m)?)?;
    Ok(())
}
