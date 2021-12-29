import io
import time
import warnings
from dataclasses import dataclass, fields
from typing import List, OrderedDict

import numpy as np

import qoi

OPENCV_AVAILABLE = False
try:
    import cv2

    OPENCV_AVAILABLE = True
except ImportError:
    warnings.warn("Couldn't find OpenCV - you can still run this, but OpenCV tests will be disabled.")

PIL_AVAILABLE = False
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    warnings.warn("Couldn't find PIL - you can still run this, but PIL tests will be disabled.")


@dataclass
class TestResult:
    method: str
    test: str
    format: str
    raw_size: int
    encode_ms: float
    encode_size: float
    decode_ms: float


def timeit(f, warmup=3, tests=10):
    for _ in range(warmup):
        f()
    t0 = time.time()
    for _ in range(tests):
        x = f()
    encode_ms = (time.time() - t0) / tests * 1000
    return encode_ms, x


def bench_qoi(rgb, test_name, warmup=3, tests=10):
    encode_ms, bites = timeit(lambda: qoi.encode(rgb), warmup=warmup, tests=tests)
    decode_ms, _ = timeit(lambda: qoi.decode(bites), warmup=warmup, tests=tests)
    yield TestResult(
        "qoi",
        test=test_name,
        format="qoi",
        raw_size=np.product(rgb.shape),
        encode_ms=encode_ms,
        encode_size=len(bites),
        decode_ms=decode_ms,
    )


def bench_pil(rgb, test_name, warmup=3, tests=10, jpg=True, png=True):
    img = Image.fromarray(rgb)

    fmts = []
    if jpg:
        fmts.append("JPEG")
    if png:
        fmts.append("PNG")
    for fmt in fmts:

        def encode():
            bites = io.BytesIO()
            img.save(bites, format=fmt)
            return bites.getbuffer()

        encode_ms, bites = timeit(encode, warmup=warmup, tests=tests)
        bites_ = io.BytesIO(bites)
        decode_ms, _ = timeit(lambda: np.asarray(Image.open(bites_)), warmup=warmup, tests=tests)
        yield TestResult(
            "PIL",
            test=test_name,
            format=fmt.lower().replace("e", ""),
            raw_size=np.product(rgb.shape),
            encode_ms=encode_ms,
            encode_size=len(bites),
            decode_ms=decode_ms,
        )


def bench_opencv(rgb, test_name, warmup=3, tests=10, jpg=True, png=True):
    exts = []
    if jpg:
        exts.append(".jpg")
    if png:
        exts.append(".png")
    for ext in exts:

        def encode():
            # Don't worry about RGB -> BGR as if we're using opencv we'd be using BGR anyway
            return cv2.imencode(ext, rgb)[1].tobytes()

        encode_ms, bites = timeit(encode, warmup=warmup, tests=tests)
        decode_ms, _ = timeit(
            lambda: cv2.imdecode(np.frombuffer(bites, np.uint8), cv2.IMREAD_COLOR), warmup=warmup, tests=tests
        )
        yield TestResult(
            "opencv",
            test=test_name,
            format=ext[1:],
            raw_size=np.product(rgb.shape),
            encode_ms=encode_ms,
            encode_size=len(bites),
            decode_ms=decode_ms,
        )


def bench_methods(rgb, name, warmup=3, tests=10, jpg=True, png=True, pil=None, opencv=None):
    yield from bench_qoi(rgb, test_name=name, warmup=warmup, tests=tests)
    if opencv is not None and opencv and not OPENCV_AVAILABLE:
        raise RuntimeError("You've explicitly requested to run OpenCV benchmarks but it isn't available!")
    if pil is not None and pil and not PIL_AVAILABLE:
        raise RuntimeError("You've explicitly requested to run PIL benchmarks but it isn't available!")
    if (opencv or opencv is None) and OPENCV_AVAILABLE:
        yield from bench_opencv(rgb, test_name=name, warmup=warmup, tests=tests, jpg=jpg, png=png)
    if (pil or pil is None) and PIL_AVAILABLE:
        yield from bench_pil(rgb, test_name=name, warmup=warmup, tests=tests, jpg=jpg, png=png)


def totable(results: List[TestResult]):

    # Sort:
    results = sorted(results, key=lambda x: (x.test, x.method, x.format))

    pretty_names = OrderedDict(
        test="Test image",
        method="Method",
        format="Format",
        raw_size="Input (kb)",
        encode_ms="Encode (ms)",
        encode_size="Encode (kb)",
        decode_ms="Decode (ms)",
    )

    # Convert to dicts of strings
    items = []
    for res in results:
        item = {}
        for k in fields(res):
            name = k.name
            v = getattr(res, name)
            if name.endswith("_ms"):
                v = f"{v:.2f}"
            elif name.endswith("_size"):
                v = f"{v/1024:.1f}"
            item[name] = str(v)
        items.append(item)

    # Add header:
    items.insert(0, pretty_names)

    # Get max length:
    maxlens = {}
    for k in items[0]:
        maxlens[k] = max(len(item[k]) for item in items)

    # Print:
    for idx, item in enumerate(items):
        vals = []
        for k in pretty_names:
            vals.append(item[k].ljust(maxlens[k]))
        print("| " + " | ".join(vals) + " |")
        if idx == 0:
            vals = []
            for k in pretty_names:
                vals.append("-" * maxlens[k])
            print("| " + " | ".join(vals) + " |")


def progress(iter):
    for res in iter:
        s = f"test={res.test}, method={res.method}, format={res.format}"
        print(s.ljust(80), end="\r")
        yield res


def benchmark(warmup=3, tests=10, jpg=True, png=True, pil=None, opencv=None):
    size = (1080, 1920, 3)
    rgb = np.zeros(size, np.uint8)
    kwargs = dict(warmup=warmup, tests=tests, jpg=jpg, png=png, pil=pil, opencv=opencv)
    results = []
    results = list(progress(bench_methods(rgb, "all black ('best' case)", **kwargs)))
    rgb = np.random.randint(low=0, high=255, size=size, dtype=np.uint8)
    results += list(progress(bench_methods(rgb, "random noise (worst case)", **kwargs)))
    totable(results)


if __name__ == "__main__":
    benchmark()
