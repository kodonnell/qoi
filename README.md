# QOI

A simple Python wrapper around [qoi](https://github.com/phoboslab/qoi), the "Quite OK Image" format.

## Install

```sh
pip install qoi
```

## Develop

Clone
```sh
git clone --recursive https://github.com/kodonnell/qoi/
```

Build
```sh
python -m pip install --upgrade build
rm -rf ./dist
python -m build sdist
```

Publish
```sh
python -m twine upload — repository testpypi dist/*
```

## TODO:

- Add in `setuptools_scm` and figure out that nicely.
- Add build/publish pipeline (inc. running tests) and wheels via `cibuildwheel`.
- Create a `qoi` CLI
- Add some benchmarks and compare with `qoi`
- Add example usage to README
- More tests!
- Allow `Path` as argument for filename.
- Why does `write` fail without a `.qoi` extension? If that's valid, raise a proper exception.
- Add version to `._version` as per `setuptools_scm` ... for some reason it breaks when we add an `__init__.py`.
- Return the colorspace in read/decode.

## Discussion

### Wrap or rewrite?

For now, this is just a simple wrapper. We'll leave the original project to do all the hard work on performance etc., and also maintaining (or not) compatibility or adding new features etc. We make no claims to do any more than that - we're basically just porting that C functionality to (C)Python.

### On the name

For now, let's rock with `qoi` because 

- We're already in python, and the `py` in `pyqoi` seems redundant. For what it's worth, `3 < 5`.
- `pyqoi` seems like a good name for a python-only version of QOI (useful for pypy etc.), which this isn't.
- `qoi` is generally new so let's not overthink it for now. We can always rename later if needed.
