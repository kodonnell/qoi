# QOI

A simple Python wrapper around [qoi](https://github.com/phoboslab/qoi), the "Quite OK Image" format.

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
```

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

### Publish

This currently is all automatic, and just needs a new tag pushed to Github in the `vX.X.X` format.

## TODO:

- Fix the `cython` project structure. I had to try a bunch of things to get the version (from `setuptools_scm` in) but it feels very fragile. I'd prefer everything in an `__init__.py` (defining imports and `__all__` etc.) but that doesn't seem to work. I also don't get why this is working as it is - I feel like there's some package/namespace magic going on (e.g. the files being called `qoi.p*` is important), but haven't been able to fix it. See maybe https://stackoverflow.com/questions/33555927/cython-relative-cimport-beyond-main-package-is-not-allowed ? Also, I think our use of `src` might be tripping us up (i.e. still valid, but needs more obscure fixing than just out-of-the-box).
- Get `cp310-win32 ` building ...
- Create a `qoi` CLI
- Add some benchmarks and compare with `qoi`
- Automatically create release on github when push a tag v*? 
- `setuptools_scm_git_archive`?
- Get cibuildwheels to do a build without `--wheel` option to ensure the source distribution is good.

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