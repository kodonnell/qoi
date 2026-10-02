[![PyPI version fury.io](https://badge.fury.io/py/qoi.svg)](https://pypi.python.org/pypi/qoi/)

# QOI

A simple Python wrapper around [QOI](https://qoiformat.org), the "Quite OK Image" image format (via the [`qoi`](https://crates.io/crates/qoi) Rust crate). It's

- Lossless with comparable compression to PNG, but fast! It encodes 4x+ faster and decodes 3x+ faster than PNG in OpenCV or PIL.
- You can make it lossy with a simple trick (downscale before encoding), and then it's around 2.5x faster than JPEG, though the files are around 2.4x bigger for the same visual quality. (These numbers vary a lot depending on how "lossy" you make JPEG or QOI.)
- Multi-threaded - no GIL hold-ups here. Encoding and decoding release the GIL, and free-threaded Python (e.g. 3.14t) is supported too.
- Zero-copy where possible - arrays are encoded from, and decoded into, numpy memory directly.

## Install

```sh
pip install qoi
```

## Example

```python
import numpy as np
import qoi

# Get your image as a numpy array (OpenCV, Pillow, etc. but here we just create a bunch of noise). Note: HWC ordering
rgb = np.random.randint(low=0, high=255, size=(224, 244, 3)).astype(np.uint8)

# Write it:
_ = qoi.write("/tmp/img.qoi", rgb)

# Read it and check it matches (it should, as we're lossless)
rgb_read = qoi.read("/tmp/img.qoi")
assert np.array_equal(rgb, rgb_read)

# Likewise for encode/decode to/from bytes:
bites = qoi.encode(rgb)
rgb_decoded = qoi.decode(bites)
assert np.array_equal(rgb, rgb_decoded)

# Benchmarking
from qoi.benchmark import benchmark
benchmark()  # Check out the arguments if you're interested
```

If you want to really max out your CPU:

```python
from concurrent.futures import ThreadPoolExecutor, wait
import numpy as np
import qoi

RGB = np.random.randint(low=0, high=255, size=(224, 244, 3)).astype(np.uint8)

def worker():
    bites = bytearray(qoi.encode(RGB))
    img_decoded = qoi.decode(bites)

print("Go watch your CPU utilization ...")
with ThreadPoolExecutor(8) as pool:
    futures = [pool.submit(worker) for _ in range(10000)]
    wait(futures)
```

## (Single-threaded) Benchmarks

If we consider lossless, then we're generally comparing with PNG. Yup, there are others, but they're not as common. Benchmarks:

| Test image                | Method | Format | Input (kb) | Encode (ms) | Encode (kb) | Decode (ms) | SSIM |
| ------------------------- | ------ | ------ | ---------- | ----------- | ----------- | ----------- | ---- |
| all black ('best' case)   | PIL    | png    | 6075.0     | 17.16       | 6.0         | 5.01        | 1.00 |
| all black ('best' case)   | opencv | png    | 6075.0     | 8.98        | 7.7         | 8.16        | 1.00 |
| all black ('best' case)   | qoi    | qoi    | 6075.0     | 1.75        | 32.7        | 0.63        | 1.00 |
| koi photo                 | PIL    | png    | 6075.0     | 801.69      | 2821.5      | 50.21       | 1.00 |
| koi photo                 | opencv | png    | 6075.0     | 51.01       | 3121.5      | 34.07       | 1.00 |
| koi photo                 | qoi    | qoi    | 6075.0     | 12.04       | 3489.0      | 8.83        | 1.00 |
| random noise (worst case) | PIL    | png    | 6075.0     | 142.37      | 6084.5      | 32.97       | 1.00 |
| random noise (worst case) | opencv | png    | 6075.0     | 33.77       | 6086.9      | 8.77        | 1.00 |
| random noise (worst case) | qoi    | qoi    | 6075.0     | 8.95        | 8096.2      | 3.07        | 1.00 |

So `qoi` isn't far off PNG in terms of compression, but 4x-60x faster to encode and 3x-13x faster to decode.

> NB:
>
> 1. There's additional overhead here with PIL images being converted back to an array as the return type, to be consistent. In some sense, this isn't fair, as PIL will be faster if you're dealing with PIL images. On the other hand, if your common use case involves arrays (e.g. for computer vision) then it's reasonable.
> 2. Produced with `python -m qoi.benchmark --implementations=qoi,opencv,pil --formats=png,qoi --tests=20` on an i7-12700H (WSL2). Not going to the point of optimised OpenCV/PIL (e.g. SIMD, or `pillow-simd`) as the results are clear enough for this 'normal' scenario. If you want to dig further, go for it! You can easily run these tests yourself.

If we consider lossy compression, again, JPEG is usually what we're comparing with. Normally, it'd be unfair to compare QOI with JPEG as QOI is lossless, however we can do a slight trick to make QOI lossy - downscale the image, then encode it, then upsample it by the same amount after decoding. You can see we've implemented that below with a downscaling to 40% and JPEG quality of 80 (which results in them having the same visual compression i.e. SSIM). So, results (only on `koi photo` as the rest are less meaningful/fair for lossy):

| Test image | Method              | Format   | Input (kb) | Encode (ms) | Encode (kb) | Decode (ms) | SSIM |
| ---------- | ------------------- | -------- | ---------- | ----------- | ----------- | ----------- | ---- |
| koi photo  | PIL                 | jpg @ 80 | 6075.0     | 5.33        | 274.6       | 6.40        | 0.94 |
| koi photo  | opencv              | jpg @ 80 | 6075.0     | 5.93        | 275.3       | 5.37        | 0.94 |
| koi photo  | qoi                 | qoi      | 6075.0     | 11.86       | 3489.0      | 8.62        | 1.00 |
| koi photo  | qoi-lossy-0.40x0.40 | qoi      | 6075.0     | 2.28        | 667.5       | 2.21        | 0.94 |

Here we see that lossless `qoi` is losing out considerably in compression, as expected for lossy vs lossless. Modern JPEG libraries (e.g. `libjpeg-turbo`, as now shipped with PIL and OpenCV) are also very fast, so lossless `qoi` is now around 2x slower to encode and 1.5x slower to decode than JPEG. Note this varies a lot depending on the jpeg quality specified - here it's 80 but the default for OpenCV is actually 95 which is 3x worse compression and a bit slower.

However, that's still lossy vs lossless! If you look at `qoi-lossy-0.40x0.40` where we downscale as above, you can see that it can perform really well. The compression ratio is now only 2.4x that of JPEG (and 5x better than lossless QOI, and also the same as the default OpenCV JPEG encoding at a quality of 95), and it's faster - around 2.5x faster to encode and decode.

Anyway, there are definitely use cases where `qoi` may still make sense over JPEG. If you use the "lossy" QOI, you're getting "comparable" (depending on JPEG quality) compression but faster.

> NB:
>
> 1. See above re additional PIL overhead.
> 2. Produced with `python -m qoi.benchmark --images=koi --implementations=qoi,qoi-lossy,opencv,pil --formats=jpg,qoi --qoi-lossy-scale=0.4 --jpeg-quality=80 --tests=20` on an i7-12700H (WSL2). Not going to the point of optimised OpenCV/PIL (e.g. `pillow-simd`, different JPEG qualities, etc.) as the results are clear enough for this 'normal' scenario. If you want to dig further, go for it! You can easily run these tests yourself.

## Developing

The extension is written in Rust (see `src/lib.rs`) using [PyO3](https://pyo3.rs), and built with [maturin](https://www.maturin.rs). You'll need a Rust toolchain - see [rustup](https://rustup.rs).

```sh
git clone https://github.com/kodonnell/qoi/
cd qoi
pip install maturin
maturin develop --release --extras dev  # builds and installs (editable) into the current environment
pytest
```

Rerun `maturin develop --release` after changing the Rust code. (Without `--release` it builds much faster, but the result is a lot slower.)

We use [maturin-action](https://github.com/PyO3/maturin-action) to build all the wheels in a GitHub action: one `abi3` wheel per platform (covering CPython 3.11+) plus a free-threaded (3.14t) wheel. If you want to check a wheel builds locally, `maturin build --release`.

Finally, when you're happy, submit a PR.

### Publishing

When you're on `main` on your local, bump the `version` in `Cargo.toml` (and commit it), then `git tag vX.X.X` (matching that version) and `git push origin vX.X.X`. This pushes the tag which triggers the full GitHub Action and:

- Checks the tag matches the version in `Cargo.toml`
- Builds source distribution and wheels (for various platforms), and tests them
- Pushes to PyPI
- Creates a new release with the appropriate artifacts attached.

## TODO

- Make `benchmark.py` a CLI entry point
- Create a `qoi` CLI
- Benchmarks - add real images, and also compare performance with QOI to see overhead of python wrapper.

## Discussion

### Wrap or rewrite?

For now, this is just a simple wrapper. We'll leave the underlying implementation to do all the hard work on performance etc., and also maintaining (or not) compatibility or adding new features etc. We make no claims to do any more than that - we're basically just porting that functionality to Python.

Up to v0.7 we wrapped the [reference C implementation](https://github.com/phoboslab/qoi) with Cython. From v0.8 we wrap the [`qoi`](https://crates.io/crates/qoi) Rust crate with PyO3, which is 1.1x-2x faster (except encoding noisy images, which is about the same), and much simpler to build and package. Things to be aware of if upgrading:

- Python 3.11+ is required.
- Files are still fully compatible both ways, but the encoded bytes for an image aren't always identical to the reference encoder's - the QOI format allows a few different (equally valid, and same size) encodings of the same pixels.
- Invalid inputs consistently raise `ValueError` (e.g. wrong `dtype`/shape, non-contiguous arrays, bad `colorspace`), and failures to encode/decode/read/write raise `RuntimeError` with more detail than before.

### On the name

For now, let's rock with `qoi` because

- We're already in python, and the `py` in `pyqoi` seems redundant. For what it's worth, `3 < 5`.
- `pyqoi` seems like a good name for a python-only version of QOI (useful for pypy etc.), which this isn't.
- `qoi` is generally new so let's not overthink it for now. We can always rename later if needed.

### What's up with `./src`?

See [here](https://hynek.me/articles/testing-packaging/) and [here](https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-structure). I didn't read all of it, but yeh, `import qoi` is annoying when there's also a folder called `qoi`.
