[![PyPI version fury.io](https://badge.fury.io/py/qoi.svg)](https://pypi.python.org/pypi/qoi/)

# QOI

A simple Python wrapper around [qoi](https://github.com/phoboslab/qoi), the "Quite OK Image" image format. It's

- Lossless with comparable compression to PNG.
- Fast! It encodes 10x faster and decodes around 5x faster than PNG in OpenCV or PIL. It's still a whole lot faster than JPEG, even though that's lossy.

## Install

```sh
pip install qoi
```

## Example

```python
import numpy as np
import qoi

# Get your image as a numpy array (OpenCV, Pillow, etc. but here we just create a bunch of noise)
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

## Benchmarks

If we consider lossless, then we're generally comparing with PNG. Yup, there are others, but they're not as common. Benchmarks:

| Test image                | Method | Format | Input (kb) | Encode (ms) | Encode (kb) | Decode (ms) |
| ------------------------- | ------ | ------ | ---------- | ----------- | ----------- | ----------- |
| all black ('best' case)   | PIL    | png    | 6075.0     | 35.54       | 6.0         | 14.94       |
| all black ('best' case)   | opencv | png    | 6075.0     | 19.93       | 7.7         | 15.18       |
| all black ('best' case)   | qoi    | qoi    | 6075.0     | 3.93        | 32.7        | 2.41        |
| random noise (worst case) | PIL    | png    | 6075.0     | 272.33      | 6084.5      | 42.28       |
| random noise (worst case) | opencv | png    | 6075.0     | 58.33       | 6086.9      | 12.93       |
| random noise (worst case) | qoi    | qoi    | 6075.0     | 15.71       | 8096.1      | 8.04        |

So `qoi` isn't far off PNG in terms of compression, but 4x-20x faster to encode and 1.5x-6x faster to decode.

> NB:
> 1. There's additional overhead here with PIL images being converted back to an array as the return type, to be consistent. In some sense, this isn't fair, as PIL will be faster if you're dealing with PIL images. On the other hand, if your common use case involves arrays (e.g. for computer vision) then it's reasonable.
> 2. Produced with `qoi.benchmark.benchmark(jpg=False)` on an i7-9750H. Not going to the point of optimised OpenCV/PIL (e.g. SIMD, or `pillow-simd`) as the results are clear enough for this 'normal' scenario. If you want to dig further, go for it! You can easily run these tests yourself.

If we consider lossy compression, again, JPEG is usually what we're comparing with. This isn't really a far comparison as QOI is lossless and JPEG is lossy, but let's see.

| Test image                | Method | Format | Input (kb) | Encode (ms) | Encode (kb) | Decode (ms) |
| ------------------------- | ------ | ------ | ---------- | ----------- | ----------- | ----------- |
| all black ('best' case)   | PIL    | jpg    | 6075.0     | 30.33       | 32.5        | 18.44       |
| all black ('best' case)   | opencv | jpg    | 6075.0     | 21.52       | 32.5        | 14.31       |
| all black ('best' case)   | qoi    | qoi    | 6075.0     | 4.29        | 32.7        | 2.60        |
| random noise (worst case) | PIL    | jpg    | 6075.0     | 97.80       | 1217.3      | 45.55       |
| random noise (worst case) | opencv | jpg    | 6075.0     | 39.62       | 2376.2      | 38.31       |
| random noise (worst case) | qoi    | qoi    | 6075.0     | 19.34       | 8096.1      | 7.90        |

Here we see that `qoi` is losing out considerably in compression, as expected for lossy vs lossless. Nonetheless, `qoi` is still 2x-6x faster to encode, and 5x-7x faster to decode. So, there are definitely use cases where `qoi` may still make sense over JPEG ... especially if you want lossless.

> NB:
> 1. See above re additional PIL overhead.
> 2. Produced with `qoi.benchmark.benchmark(png=False)` on an i7-9750H. Not going to the point of optimised OpenCV/PIL (e.g. SIMD, or `pillow-simd`, `libjpeg-turbo`, different JPEG qualities, etc.) as the results are clear enough for this 'normal' scenario. If you want to dig further, go for it! You can easily run these tests yourself.

## Developing

```sh
git clone --recursive https://github.com/kodonnell/qoi/
USE_CYTHON=1 pip install -e .[dev]
pytest .
```

We use `cibuildwheel` to build all the wheels, which runs in a Github action. If you want to check this succeeds locally, you can try (untested):

```sh
cibuildwheel --platform linux .
```

Finally, when you're happy, submit a PR.

### Publishing

When you're on `main` on your local, `git tag vX.X.X` then `git push origin vX.X.X`. This pushes the tag which triggers the full GitHub Action and:

- Builds source distribution and wheels (for various platforms)
- Pushes to PyPI
- Creates a new release with the appropriate artifacts attached.

## TODO:

- Get `cp310-win32 ` building ...
- Create a `qoi` CLI
- Benchmarks - add real images, and also compare performance with QOI to see overhead of python wrapper.
- `setuptools_scm_git_archive`?
- Code completion?
- Investigate a simple 'lossy' compression with QOI - halve the image size and compress, and on decode, just upscale. It'll likely be very visually similar, but also much smaller, but should compare with JPEG.

## Discussion

### Wrap or rewrite?

For now, this is just a simple wrapper. We'll leave the original project to do all the hard work on performance etc., and also maintaining (or not) compatibility or adding new features etc. We make no claims to do any more than that - we're basically just porting that C functionality to (C)Python.

### On the name

For now, let's rock with `qoi` because 

- We're already in python, and the `py` in `pyqoi` seems redundant. For what it's worth, `3 < 5`.
- `pyqoi` seems like a good name for a python-only version of QOI (useful for pypy etc.), which this isn't.
- `qoi` is generally new so let's not overthink it for now. We can always rename later if needed.

### What's up with `./src`?!

See [here](https://hynek.me/articles/testing-packaging/) and [here](https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-structure). I didn't read all of it, but yeh, `import qoi` is annoying when there's also a folder called `qoi`.

### `USE_CTYHON=1`?

See [here](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#distributing-cython-modules). Fair point.