import os
from unittest import TestCase

import memtrace

current_dir = os.path.dirname(__file__)


class TestMemory(TestCase):
    def setUp(self):
        self.state = memtrace.State([(r"PyMem_RawMalloc (?P<addr>\w+)", r"PyMem_RawFree (?P<addr>\w+)")])
        pass

    def tearDown(self):
        pass

    def test_memory(self):
        with open(os.path.join(current_dir, "memory.log"), encoding="utf-16") as f:
            memtrace.parse_log(f, self.state)


if __name__ == '__main__':
    import unittest

    unittest.main()