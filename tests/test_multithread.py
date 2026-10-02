import os
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
import qoi

RGB = np.random.randint(low=0, high=255, size=(224, 244, 3)).astype(np.uint8)


def worker():
    bites = bytearray(qoi.encode(RGB))
    decoded = qoi.decode(bites)
    assert np.array_equal(RGB, decoded)


def test_multithreaded():
    """
    Note that this doesn't really test the performance, but it at least validates that it runs multithreaded.
    """
    with ThreadPoolExecutor(8) as pool:
        futures = [pool.submit(worker) for _ in range(100)]
        for f in futures:
            f.result()  # re-raises any assertion errors from the worker


@pytest.mark.skipif((os.cpu_count() or 1) < 2, reason="needs multiple cores")
def test_releases_gil():
    """
    If encode/decode hold the GIL then threads can't speed things up. So check they do, with a generous margin to avoid
    flakiness on busy machines.
    """
    img = np.random.randint(low=0, high=255, size=(1080, 1920, 3), dtype=np.uint8)
    encoded = qoi.encode(img)
    n_jobs, n_threads = 8, 2

    def job(_):
        qoi.decode(qoi.encode(img))
        qoi.decode(encoded)

    def best_of_3(f):
        times = []
        for _ in range(3):
            t0 = time.perf_counter()
            f()
            times.append(time.perf_counter() - t0)
        return min(times)

    with ThreadPoolExecutor(n_threads) as pool:
        list(pool.map(job, range(n_threads)))  # warm up
        serial = best_of_3(lambda: list(map(job, range(n_jobs))))
        parallel = best_of_3(lambda: list(pool.map(job, range(n_jobs))))
    assert parallel < 0.8 * serial, f"no speedup from threads: {serial=:.3f}s {parallel=:.3f}s"
