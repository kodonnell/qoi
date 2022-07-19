from concurrent.futures import ThreadPoolExecutor, wait

import numpy as np

import qoi

RGB = np.random.randint(low=0, high=255, size=(224, 244, 3)).astype(np.uint8)
RGBA = np.random.randint(low=0, high=255, size=(224, 244, 4)).astype(np.uint8)


def worker():
    bites = bytearray(qoi.encode(RGB))
    img_decoded = qoi.decode(bites)
    # print("done")


def main():
    with ThreadPoolExecutor(8) as pool:
        futures = [pool.submit(worker) for _ in range(10000)]
        wait(futures)
    print("Did you see that in top? Congratulations you have bypass the gil")

if __name__ == "__main__":
    main()
