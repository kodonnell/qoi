import io
import re
import time
import warnings
from dataclasses import dataclass, fields
from pathlib import Path
from typing import List, OrderedDict

import numpy as np

import qoi

OPENCV_AVAILABLE = False
try:
    import cv2

    OPENCV_AVAILABLE = True
except ImportError:
    warnings.warn(
        (
            "Couldn't find OpenCV - you can still run this, but OpenCV tests/functionality will be disabled, including"
            " lossy qoi (which uses OpenCV to resize the image)"
        )
    )

PIL_AVAILABLE = False
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    warnings.warn("Couldn't find PIL - you can still run this, but PIL tests will be disabled.")

try:
    from skimage.metrics import structural_similarity as img_similarity

    similarity_name = "SSIM"
except ImportError:
    warnings.warn("Couldn't find skimage.metrics.structural_similarity so using MSE.")

    def img_similarity(a, b, channel_axis=None):
        return ((a - b) ** 2).mean()

    similarity_name = "MSE"


@dataclass
class TestResult:
    method: str
    test: str
    format: str
    raw_size: int
    encode_ms: float
    encode_size: float
    decode_ms: float
    img_similarity: float


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
    decode_ms, decoded = timeit(lambda: qoi.decode(bites), warmup=warmup, tests=tests)
    yield TestResult(
        "qoi",
        test=test_name,
        format="qoi",
        raw_size=np.product(rgb.shape),
        encode_ms=encode_ms,
        encode_size=len(bites),
        decode_ms=decode_ms,
        img_similarity=img_similarity(rgb, decoded, channel_axis=2),
    )


def bench_qoi_lossy(rgb, test_name, warmup=3, tests=10, scale=0.5):
    def encode():
        return qoi.encode(cv2.resize(rgb, dsize=None, fx=scale, fy=scale))

    encode_ms, bites = timeit(encode, warmup=warmup, tests=tests)

    def decode():
        return cv2.resize(qoi.decode(bites), dsize=None, fx=1 / scale, fy=1 / scale)

    decode_ms, decoded = timeit(decode, warmup=warmup, tests=tests)
    yield TestResult(
        f"qoi-lossy-{scale:0.2f}x{scale:0.2f}",
        test=test_name,
        format="qoi",
        raw_size=np.product(rgb.shape),
        encode_ms=encode_ms,
        encode_size=len(bites),
        decode_ms=decode_ms,
        img_similarity=img_similarity(rgb, decoded, channel_axis=2),
    )


def bench_pil(rgb, test_name, warmup=3, tests=10, jpg=True, png=True, jpeg_quality=80):
    img = Image.fromarray(rgb)

    fmts = []
    if jpg:
        fmts.append("JPEG")
    if png:
        fmts.append("PNG")
    for fmt in fmts:

        if fmt == "JPEG":
            format = f"jpg @ {jpeg_quality}"

            def encode():
                bites = io.BytesIO()
                img.save(bites, format=fmt, quality=jpeg_quality)
                return bites.getbuffer()

        else:
            format = "png"

            def encode():
                bites = io.BytesIO()
                img.save(bites, format=fmt)
                return bites.getbuffer()

        encode_ms, bites = timeit(encode, warmup=warmup, tests=tests)
        bites_ = io.BytesIO(bites)
        decode_ms, decoded = timeit(lambda: np.asarray(Image.open(bites_)), warmup=warmup, tests=tests)
        yield TestResult(
            "PIL",
            test=test_name,
            format=format,
            raw_size=np.product(rgb.shape),
            encode_ms=encode_ms,
            encode_size=len(bites),
            decode_ms=decode_ms,
            img_similarity=img_similarity(rgb, decoded, channel_axis=2),
        )


def bench_opencv(rgb, test_name, warmup=3, tests=10, jpg=True, png=True, jpeg_quality=80):
    exts = []
    if jpg:
        exts.append(".jpg")
    if png:
        exts.append(".png")
    for ext in exts:

        # Don't worry about RGB -> BGR as if we're using opencv we'd be using BGR anyway
        if ext == ".jpg":
            format = f"jpg @ {jpeg_quality}"

            def encode():
                return cv2.imencode(ext, rgb, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])[1].tobytes()

        else:
            format = "png"

            def encode():
                return cv2.imencode(ext, rgb)[1].tobytes()

        encode_ms, bites = timeit(encode, warmup=warmup, tests=tests)
        decode_ms, decoded = timeit(
            lambda: cv2.imdecode(np.frombuffer(bites, np.uint8), cv2.IMREAD_COLOR), warmup=warmup, tests=tests
        )
        yield TestResult(
            "opencv",
            test=test_name,
            format=format,
            raw_size=np.product(rgb.shape),
            encode_ms=encode_ms,
            encode_size=len(bites),
            decode_ms=decode_ms,
            img_similarity=img_similarity(rgb, decoded, channel_axis=2),
        )


def bench_methods(
    rgb, name, warmup=3, tests=10, formats=None, implementations=None, qoi_lossy_scale=0.5, jpeg_quality=80
):
    jpg = formats is None or "jpg" in formats
    png = formats is None or "png" in formats
    qoi = formats is None or "qoi" in formats
    if implementations is not None and "opencv" in implementations and not OPENCV_AVAILABLE:
        raise RuntimeError("You've explicitly requested to run OpenCV benchmarks but it isn't available!")
    if implementations is not None and "pil" in implementations and not PIL_AVAILABLE:
        raise RuntimeError("You've explicitly requested to run PIL benchmarks but it isn't available!")
    if (implementations is None or "opencv" in implementations) and OPENCV_AVAILABLE:
        yield from bench_opencv(
            rgb, test_name=name, warmup=warmup, tests=tests, jpg=jpg, png=png, jpeg_quality=jpeg_quality
        )
    if (implementations is None or "pil" in implementations) and PIL_AVAILABLE:
        yield from bench_pil(
            rgb, test_name=name, warmup=warmup, tests=tests, jpg=jpg, png=png, jpeg_quality=jpeg_quality
        )
    if qoi and (implementations is None or "qoi" in implementations):
        yield from bench_qoi(rgb, test_name=name, warmup=warmup, tests=tests)
    if qoi and (implementations is None or "qoi-lossy" in implementations) and OPENCV_AVAILABLE:
        yield from bench_qoi_lossy(rgb, test_name=name, warmup=warmup, tests=tests, scale=qoi_lossy_scale)


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
        img_similarity=similarity_name,
    )

    # Convert to dicts of strings
    items = []
    for res in results:
        item = {}
        for k in fields(res):
            name = k.name
            v = getattr(res, name)
            if name == "img_similarity" or name.endswith("_ms"):
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


def benchmark(
    warmup=3, tests=10, images=".*", formats=None, implementations=None, qoi_lossy_scale=0.5, jpeg_quality=90
):
    size = (1080, 1920, 3)
    kwargs = dict(
        warmup=warmup,
        tests=tests,
        formats=formats,
        implementations=implementations,
        qoi_lossy_scale=qoi_lossy_scale,
        jpeg_quality=jpeg_quality,
    )
    p = re.compile(images)
    results = []
    name = "all black ('best' case)"
    if p.match(name):
        rgb = np.zeros(size, np.uint8)
        results += list(progress(bench_methods(rgb, name, **kwargs)))
    name = "random noise (worst case)"
    if p.match(name):
        rgb = np.random.randint(low=0, high=255, size=size, dtype=np.uint8)
        results += list(progress(bench_methods(rgb, name, **kwargs)))
    name = "koi photo"
    # Nedd opencv to load image
    if p.match(name) and OPENCV_AVAILABLE:
        rgb = cv2.cvtColor(cv2.imread(str(Path(__file__).parent.resolve() / "koi.png")), cv2.COLOR_BGR2RGB)
        results += list(progress(bench_methods(rgb, name, **kwargs)))
    totable(results)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--images", default=".*", help="regex to mach the image name")
    parser.add_argument("--formats", default=None, help="Comma separated values of formats to test")
    parser.add_argument("--implementations", default=None, help="Comma separated values of implementations to test")
    parser.add_argument("--warmup", type=int, default=3, help="Warmup iterations")
    parser.add_argument("--tests", type=int, default=10, help="Test iterations")
    parser.add_argument("--qoi-lossy-scale", type=float, default=0.5, help="The scale when doing lossy qoi.")
    parser.add_argument("--jpeg-quality", type=int, default=80, help="The jpeg encode quality.")
    args = parser.parse_args()
    benchmark(
        images=args.images,
        warmup=args.warmup,
        tests=args.tests,
        formats=None if args.formats is None else args.formats.lower().split(","),
        implementations=None if args.implementations is None else args.implementations.lower().split(","),
        qoi_lossy_scale=args.qoi_lossy_scale,
        jpeg_quality=args.jpeg_quality,
    )
