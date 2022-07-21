[![PyPI version fury.io](https://badge.fury.io/py/qoi.svg)](https://pypi.python.org/pypi/qoi/)

# QOI

A simple Python wrapper around [qoi](https://github.com/phoboslab/qoi), the "Quite OK Image" image format. It's

- Lossless with comparable compression to PNG, but fast! It encodes 10x faster and decodes around 5x faster than PNG in OpenCV or PIL.
- You can make it lossy with a simple trick, and then you can get similar compression to JPEG but a whole lot faster. (These number vary a lot depending on how "lossy" you make JPEG or QOI). That's cool.
- Multi-threaded - no GIL hold-ups here.

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
| all black ('best' case)   | PIL    | png    | 6075.0     | 37.75       | 6.0         | 16.04       | 1.00 |
| all black ('best' case)   | opencv | png    | 6075.0     | 23.82       | 7.7         | 17.93       | 1.00 |
| all black ('best' case)   | qoi    | qoi    | 6075.0     | 4.13        | 32.7        | 2.67        | 1.00 |
| koi photo                 | PIL    | png    | 6075.0     | 849.07      | 2821.5      | 85.46       | 1.00 |
| koi photo                 | opencv | png    | 6075.0     | 95.24       | 3121.5      | 44.34       | 1.00 |
| koi photo                 | qoi    | qoi    | 6075.0     | 28.37       | 3489.0      | 17.19       | 1.00 |
| random noise (worst case) | PIL    | png    | 6075.0     | 300.37      | 6084.5      | 46.30       | 1.00 |
| random noise (worst case) | opencv | png    | 6075.0     | 63.72       | 6086.9      | 14.01       | 1.00 |
| random noise (worst case) | qoi    | qoi    | 6075.0     | 16.16       | 8096.1      | 7.67        | 1.00 |

So `qoi` isn't far off PNG in terms of compression, but 4x-20x faster to encode and 1.5x-6x faster to decode.

> NB:
>
> 1. There's additional overhead here with PIL images being converted back to an array as the return type, to be consistent. In some sense, this isn't fair, as PIL will be faster if you're dealing with PIL images. On the other hand, if your common use case involves arrays (e.g. for computer vision) then it's reasonable.
> 2. Produced with `python src/qoi/benchmark.py --implementations=qoi,opencv,pil --formats=png,qoi` on an i7-9750H. Not going to the point of optimised OpenCV/PIL (e.g. SIMD, or `pillow-simd`) as the results are clear enough for this 'normal' scenario. If you want to dig further, go for it! You can easily run these tests yourself.

If we consider lossy compression, again, JPEG is usually what we're comparing with. Normally, it'd be unfair to compare QOI with JPEG as QOI is lossless, however we can do a slight trick to make QOI lossy - downscale the image, then encode it, then upsample it by the same amount after decoding. You can see we've implemented that below with a downscaling to 40% and JPEG quality of 80 (which results in them having the same visual compression i.e. SSIM). So, results (only on `koi photo` as the rest are less meaningful/fair for lossy):

| Test image                | Method              | Format   | Input (kb) | Encode (ms) | Encode (kb) | Decode (ms) | SSIM |
| ------------------------- | ------------------- | -------- | ---------- | ----------- | ----------- | ----------- | ---- |
| koi photo                 | PIL                 | jpg @ 80 | 6075.0     | 47.67       | 275.2       | 24.01       | 0.94 |
| koi photo                 | opencv              | jpg @ 80 | 6075.0     | 24.03       | 275.3       | 19.58       | 0.94 |
| koi photo                 | qoi                 | qoi      | 6075.0     | 23.17       | 3489.0      | 12.94       | 1.00 |
| koi photo                 | qoi-lossy-0.40x0.40 | qoi      | 6075.0     | 4.38        | 667.5       | 2.96        | 0.94 |

Here we see that lossless `qoi` is losing out considerably in compression, as expected for lossy vs lossless. Also, `qoi` is only 1x-2x faster of encoding, and 1.5x-2x faster for decoding. However, it's important to note that this varies a lot depending on the jpeg quality specified - here it's 80 but the default for OpenCV is actually 95 which is 3x worse compression and a bit slower.

However, that's still lossy vs lossless! If you look at `qoi-lossy-0.40x0.40` where we downscale as above, you can see that it can perform really well. The compression ratio is now only 3x that of JPEG (and 5x better than lossless QOI, and also the same as the default OpenCV JPEG encoding at a quality of 95), but it's so fast - 5x-10x faster encoding, and 7x-8x faster decoding.

Anyway, there are definitely use cases where `qoi` may still make sense over JPEG. Even lossless QOI can be worth it if size isn't an issue, as it's a bit faster. But if you use the "lossy" QOI, you're getting "comparable" (depending on JPEG quality) compression but much faster.

> NB:
>
> 1. See above re additional PIL overhead.
> 2. Produced with `python src/qoi/benchmark.py --images=koi --implementations=qoi,qoi-lossy,opencv,pil --formats=jpg,qoi --qoi-lossy-scale=0.4 --jpeg-quality=0.8` on an i7-9750H. Not going to the point of optimised OpenCV/PIL (e.g. SIMD, or `pillow-simd`, `libjpeg-turbo`, different JPEG qualities, etc.) as the results are clear enough for this 'normal' scenario. If you want to dig further, go for it! You can easily run these tests yourself.

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

## TODO

- Make `benchmark.py` a CLI in setup.py
- Create a `qoi` CLI
- Benchmarks - add real images, and also compare performance with QOI to see overhead of python wrapper.
- `setuptools_scm_git_archive`?
- Code completion?

## Discussion

### Wrap or rewrite?

For now, this is just a simple wrapper. We'll leave the original project to do all the hard work on performance etc., and also maintaining (or not) compatibility or adding new features etc. We make no claims to do any more than that - we're basically just porting that C functionality to (C)Python.

### On the name

For now, let's rock with `qoi` because

- We're already in python, and the `py` in `pyqoi` seems redundant. For what it's worth, `3 < 5`.
- `pyqoi` seems like a good name for a python-only version of QOI (useful for pypy etc.), which this isn't.
- `qoi` is generally new so let's not overthink it for now. We can always rename later if needed.

### What's up with `./src`?

See [here](https://hynek.me/articles/testing-packaging/) and [here](https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-structure). I didn't read all of it, but yeh, `import qoi` is annoying when there's also a folder called `qoi`.

### `USE_CYTHON=1`?

See [here](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html#distributing-cython-modules). Fair point.
