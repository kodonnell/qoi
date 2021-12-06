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

### Clone
```sh
git clone --recursive https://github.com/kodonnell/qoi/
```

### Dev
```sh
USE_CYTHON=1 pip install -e .[dev]
# Make your changes, and ensure you re-run the above if it's to the cython files ...
```


### Test
```sh
pytest .
```

### Build and publish

We're using `setuptools_scm` for versioning which basically means, once you're happy with your code and it's passing tests, first:

```
rm -rf ./build
USE_CYTHON=1 python -m build
```

This checks that the code compiles *from the sdist that gets created*. This is important if you're messing round with build options etc. 

Then

```sh
git commit -a -m "..., ready for release!"
git tag "vX.X.X"
rm -rf ./build
rm -rf ./dist
USE_CYTHON=1 python -m build --sdist
python -m twine upload --repository testpypi dist/*
python -m twine upload --repository pypi dist/*
```

> NB: in future we'll have this automated as part of a Github Action etc.


## TODO:

- Add build/publish pipeline (inc. running tests) and wheels via `cibuildwheel`.
- Create a `qoi` CLI
- Add some benchmarks and compare with `qoi`
- Why does `write` fail without a `.qoi` extension? If that's valid, raise a proper exception in Python so users know what's goin on.
- Return the colorspace in read/decode.

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