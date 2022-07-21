from concurrent.futures import ThreadPoolExecutor, wait

import numpy as np
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
        wait(futures)
