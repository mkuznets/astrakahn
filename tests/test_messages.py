#!/usr/bin/env python3

import sys
sys.path[0:0] = ['..', '../..']


import unittest
from communication import SegmentationMark, Record

class TestRecord(unittest.TestCase):

    def test_init(self):

        try:
            m = Record({'foo': 'bar'})
            m = Record({})

        except Exception:
            self.fail('No exception expected.')

        with self.assertRaises(TypeError):
           Record('foo')

    def test_len(self):
        l = 324
        m = Record({k: k+1 for k in range(l)})
        self.assertEqual(len(m), l)

    def test_index(self):
        m = Record({'1': 1.0, '2': 2, '3': 'three'})
        l = len(m)

        self.assertEqual(m['2'], 2)

        # Add new value
        m['4'] = 4+0j
        self.assertEqual(len(m), l+1)
        self.assertEqual(m['4'], 4+0j)

        # Replace an existing value
        m['2'] = '2.000'
        self.assertEqual(len(m), l+1)
        self.assertEqual(m['2'], '2.000')

    def test_extract_exceptions(self):

        m = Record({'1': 1.0, '2': 2, '3': 'three'})

        with self.assertRaises(TypeError):
            m.extract(345)

        with self.assertRaises(TypeError):
            m.extract('foo')

        with self.assertRaises(TypeError):
            m.extract([213, 421])

        # Unhashable type as a label.
        with self.assertRaises(TypeError):
            m.extract([{}])

        with self.assertRaises(ValueError):
            m.extract(['', 'a'])

        with self.assertRaises(TypeError):
            m.extract(['1'], 54)

        with self.assertRaises(ValueError):
            m.extract(['1'], '')

        with self.assertRaises(IndexError):
            m.extract(['1', '2'], '1')

    def test_union(self):

        m1 = Record({'1': 1.0, '2': 2, '3': 'three'})
        m2 = Record({'2': 2.0, '4': 'four point zero'})

        m1.union(m2)

        self.assertIn('4', m1)
        self.assertEqual(m1['2'], 2.0)
        self.assertEqual(m1['4'], m2['4'])

    def test_extract(self):

        keys = set(str(i) for i in range(1000))

        d = {k: int(k)+1 for k in keys}
        m = Record(d)

        def _check(mm, ext):

            for i in ext:
                self.assertIn(i, m)

            self.assertEqual(len(mm), len(ext))

            for k in ext:
                self.assertEqual(mm[k], int(k)+1)

        ext = {'34', '944', '135', '1'}
        mm = m.extract(ext)
        _check(mm, ext)

        ext_tail = keys - ext
        mm = m.extract(ext, 'rest')
        _check(mm['rest'], ext_tail)


    def test_contains(self):

        d = {'1': 1.0, '2': 2, '3': 'three', (1, 8): 'one eight'}
        m = Record(d)

        self.assertIn('1', m)
        self.assertIn((1, 8), m)
        [self.assertIn(k, m) for k in d.keys()]

        self.assertNotIn('12', m)

    def test_repr(self):

        import re

        m = Record({'1': 1.0, '2': 2, '3': 'three'})

        match = re.match('record\(((.+?)\: (.+?))*\)', str(m))
        self.assertTrue(bool(match))

    def test_copy(self):

        m = Record({'1': 1.0, '2': 2, '3': 'three'})
        mc = m.copy()

        self.assertEqual(m.content, mc.content)
        self.assertNotEqual(id(m.content), id(mc.content))
        self.assertNotEqual(id(m), id(mc))

    def test_pop(self):

        m = Record({'1': 1.0, '2': 2, '3': 'three'})

        with self.assertRaises(TypeError):
            m.pop('a', 1, 2)

        with self.assertRaises(IndexError):
            m.pop('a')

        self.assertEqual(m.pop('1'), 1.0)
        self.assertNotIn('1', m)


class TestSegmentationMark(unittest.TestCase):

    def test_init_empty(self):

        with self.assertRaises(ValueError):
           SegmentationMark()

    def test_init_int(self):

        m = SegmentationMark(10)
        self.assertEqual(m.n, 10)
        self.assertTrue(m.is_segmark())

        with self.assertRaises(ValueError):
           SegmentationMark(-1)

        with self.assertRaises(TypeError):
           SegmentationMark('str')

    def test_init_str(self):

        m = SegmentationMark(nstr='))))((((')
        self.assertEqual(m.n, 4)
        self.assertTrue(m.is_segmark())

        m = SegmentationMark(nstr='')
        self.assertEqual(m.n, 0)

        m = SegmentationMark(nstr='sigma_0')
        self.assertEqual(m.n, 0)

        with self.assertRaises(TypeError):
           SegmentationMark(nstr=(')', ')', '(', '('))

        with self.assertRaises(ValueError):
           SegmentationMark(nstr='fail')

        with self.assertRaises(ValueError):
           SegmentationMark(nstr='))(')

        with self.assertRaises(ValueError):
           SegmentationMark(nstr=')((')

        with self.assertRaises(ValueError):
           SegmentationMark(nstr='((()))')

        with self.assertRaises(ValueError):
           SegmentationMark(nstr=']][[')

    def test_record(self):

        m = SegmentationMark(23)
        self.assertEqual(m['__n__'], 23)

        m = SegmentationMark(nstr='))))((((')
        self.assertEqual(m['__n__'], 4)

        m['abc'] = 'b'
        self.assertIn('abc', m)
        self.assertEqual(m['abc'], 'b')

    def test_union(self):
        # Union for segmark must prerve its depth.

        sm1 = SegmentationMark(23)
        sm2 = SegmentationMark(5)
        sm2['foo'] = 'bar'

        sm1.union(sm2)

        self.assertEqual(sm1.n, 23)
        self.assertIn('foo', sm1)
        self.assertEqual(sm1['foo'], 'bar')

    def test_extract(self):
        # __n__ should be is filtered from the pattern matching tail.

        m = SegmentationMark(23)
        m['foo'] = 1
        m['bar'] = 2

        match = m.extract(['foo'], 'rest')
        self.assertNotIn('__n__', match['rest'])

    def test_operations(self):

        m = SegmentationMark(0)
        m.plus()
        self.assertEqual(m.n, 0)
        #

        m = SegmentationMark(23)
        m.plus()
        self.assertEqual(m.n, 24)
        #

        m = SegmentationMark(24)
        m.minus()
        self.assertEqual(m.n, 23)
        #

        m = SegmentationMark(0)
        with self.assertRaises(ValueError):
            m.minus()

    def test_end_of_stream(self):

        m = SegmentationMark(0)
        self.assertTrue(m.end_of_stream())

        m = SegmentationMark(1)
        self.assertFalse(m.end_of_stream())

    def test_repr(self):

        for i in (0, 1, 100, 153414):
            m = SegmentationMark(i)
            mm = SegmentationMark(nstr=str(m))
            self.assertEqual(mm.n, i)

    def test_copy(self):

        m = SegmentationMark(24)
        mc = m.copy()

        self.assertEqual(m.n, mc.n)
        self.assertEqual(m.content, mc.content)
        self.assertNotEqual(id(m.content), id(mc.content))
        self.assertNotEqual(id(m), id(mc))


if __name__ == '__main__':
    unittest.main()
