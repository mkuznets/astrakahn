#!/usr/bin/env python3

# SLOPPY HACK
import sys, os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

from network import *
import unittest
import random as rand
import components as comp

class TestNetwork(unittest.TestCase):

    def test_box_spec(self):

        ni = rand.randint(1, 1000)
        no = rand.randint(1, 1000)

        # Unrecognizable box category.
        with self.assertRaises(ValueError):
            b = box_spec('dsf32')

        correct_variants = [
            ('Transductor', str(no) + 'T', comp.Transductor, 1, no, None, None),
            ('Inductor', str(no) + 'I', comp.Inductor, 1, no, None, None),
            ('Dyadic Ordered Reductor', str(no) + 'DO', comp.Reductor, 2, no, True, False),
            ('Dyadic Unordered Reductor', str(no) + 'DU', comp.Reductor, 2, no, False, True),
            ('Monadic Ordered Reductor', str(no) + 'MO', comp.Reductor, 1, no, True, False),
            ('Monadic Unordered Reductor', str(no) + 'MU', comp.Reductor, 1, no, False, True),
            ('Monadic Segmented Reductor', str(no) + 'MS', comp.Reductor, 1, no, True, True),
            ('Consumer', 'C' + str(ni), comp.Consumer, ni, 0, None, None),
            ('Producer', str(no) + 'P', comp.Producer, 1, no, None, None),
            ('Repeater', str(no) + 'R' + str(ni), comp.Repeater, ni, no, None, None),
            ('Synchroniser', str(no) + 'S' + str(ni), comp.Synchroniser, ni, no, None, None),
        ]

        margin = max(len(v[0]) for v in correct_variants) + 3

        print('box_spec(): test correct vertex categories.')
        for v in correct_variants:
            b = box_spec(v[1])
            print(' ' * 3, v[0], end=' ' * (margin - len(v[0])))
            self.assertEqual(b.box, v[2])
            self.assertEqual(b.n_inputs, v[3])
            self.assertEqual(b.n_outputs, v[4])
            self.assertEqual(b.ordered, v[5])
            self.assertEqual(b.segmentable, v[6])
            print("ok")

if __name__ == '__main__':
    unittest.main()
