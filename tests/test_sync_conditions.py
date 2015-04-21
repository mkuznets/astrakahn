#!/usr/bin/env python3

import sys
sys.path[0:0] = ['..', '../..']


import unittest
import compiler.sync.backend as sync_backend
import communication as comm

class TestConditions(unittest.TestCase):

    def test_abstract(self):

        c = sync_backend.Condition()

        with self.assertRaises(NotImplementedError):
            c.test()

    def test_pass(self):
        c = sync_backend.ConditionPass()
        self.assertTrue(c.test())

    def test_data(self):

        ms = comm.SegmentationMark(23)
        m = comm.Record({'foo': 1, 'bar': 2, 'baz': 3})

        c = sync_backend.ConditionData()
        self.assertTrue(c.test(m))
        self.assertEqual(c.locals, {})

        c = sync_backend.ConditionData()
        self.assertFalse(c.test(ms))
        self.assertEqual(c.locals, {})

        c = sync_backend.ConditionData(['foo'])
        self.assertTrue(c.test(m))
        self.assertEqual(c.locals, {'foo': 1})

        c = sync_backend.ConditionData(['tree'])
        self.assertFalse(c.test(m))
        self.assertEqual(c.locals, {})

        c = sync_backend.ConditionData(['foo'], 'rest')
        self.assertTrue(c.test(m))
        self.assertEqual(c.locals, {'foo': 1, 'rest': {'bar': 2, 'baz': 3}})

        c = sync_backend.ConditionData(['foo', 'bar', 'baz'], 'rest')
        self.assertTrue(c.test(m))
        self.assertEqual(c.locals, {'foo': 1, 'bar': 2, 'baz': 3, 'rest': {}})

    def test_segmark(self):

        ms = comm.SegmentationMark(23)
        md = comm.Record({'foo': 1, 'bar': 2, 'baz': 3})

        c = sync_backend.ConditionSegmark('d')
        self.assertTrue(c.test(ms))
        self.assertEqual(c.locals, {'d': 23})

        c = sync_backend.ConditionSegmark('d')
        self.assertFalse(c.test(md))
        self.assertEqual(c.locals, {})

        c = sync_backend.ConditionSegmark('d', ['tree'])
        self.assertFalse(c.test(ms))
        self.assertEqual(c.locals, {})

        ms['tree'] = -1
        ms['foobar'] = -2

        c = sync_backend.ConditionSegmark('d', ['tree'])
        self.assertTrue(c.test(ms))
        self.assertEqual(c.locals, {'d': 23, 'tree': -1})

        c = sync_backend.ConditionSegmark('d', ['tree'], 'rest')
        self.assertTrue(c.test(ms))
        self.assertEqual(c.locals, {'d': 23, 'tree': -1, 'rest': {'foobar': -2}})


if __name__ == '__main__':
    unittest.main()
