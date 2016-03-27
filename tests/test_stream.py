#!/usr/bin/env python3

import sys
sys.path[0:0] = ['..', '../..']


import unittest
from akr.stream import *


class TestParser(unittest.TestCase):

    def test_valid(self):

        testcases = [
            # (seq, number of elem, depth)
            ([1, 2, 3, 4, 5, 6], 6, 0),
            ([[1, 2, 3], [4, 5, 6]], 6, 1),
            ([[[1, 2]], [[3, 4]], [[5, 6]]], 6, 2),
        ]

        factory = Stream()

        for inp, n, depth in testcases:
            s = factory.read(inp)

            self.assertEqual(len(s), n)
            self.assertEqual(factory.depth, depth)

    def test_invalid(self):

        testcases = [
            [1, [2]],
            [[2], 3],
        ]

        for inp in testcases:
            factory = Stream()

            with self.assertRaises(ValueError):
                s = factory.read(inp)

if __name__ == '__main__':
    unittest.main()
