#!/usr/bin/env python3

import sys
sys.path[0:0] = ['..', '../..']


import unittest
from compiler.sync.backend import BaseExp, DataExp, TermThis, TermVar, \
    TermVarExpand, TermPair, IntExp, RecordExp, SegmentationMarkExp
import communication as comm

class TestConditions(unittest.TestCase):

    def test_abstract(self):

        exp = BaseExp()

        with self.assertRaises(NotImplementedError):
            exp.compute({})

    def test_this(self):

        exp = TermThis()

        with self.assertRaises(AssertionError):
            exp.compute({})

        with self.assertRaises(AssertionError):
            exp.compute({'__this__': 35})

        #---

        m = comm.Record({'foo': 'bar'})
        this = exp.compute({'__this__': m, 'zz': 100})

        self.assertEqual(id(this), id(m))
        self.assertIn('foo', this)

    def test_var(self):

        with self.assertRaises(TypeError):
            TermVar(4)

        exp = TermVar('foo')

        with self.assertRaises(RuntimeError):
            exp.compute({'bar': 5})

        m = comm.SegmentationMark(10)
        value = exp.compute({'foo': m, 'zz': 100})
        self.assertEqual(id(value), id(m))

    def test_var_expand(self):

        with self.assertRaises(TypeError):
            TermVarExpand(4)

        exp = TermVarExpand('foo')

        with self.assertRaises(RuntimeError):
            exp.compute({'bar': 5})

        def _test(m):
            pair = exp.compute({'foo': m, 'zz': 100})
            self.assertEqual(type(pair), comm.Record)
            self.assertEqual(pair.content, {'foo': m})

        _test(comm.SegmentationMark(10))
        _test(100)

    def test_pair(self):

        term_var = TermVar('foo')
        term_this = TermThis()
        m = comm.SegmentationMark(10)

        with self.assertRaises(TypeError):
            TermPair(42, term_var)

        with self.assertRaises(TypeError):
            TermPair('bar', 42)

        with self.assertRaises(TypeError):
            TermPair({}, 42)

        #--

        term_pair = TermPair('bar', term_var)
        value = term_pair.compute({'foo': m, 'zz': 100})
        self.assertIs(type(value), comm.Record)
        self.assertEqual(value.content, {'bar': m})

        #--

        term_pair = TermPair('bar', term_this)

        with self.assertRaises(AssertionError):
            term_pair.compute({'bar': m, 'zz': 100})

        value = term_pair.compute({'__this__': m})
        self.assertIs(type(value), comm.Record)
        self.assertEqual(value.content, {'bar': m})

    def test_int_exp(self):

        code = 'x**3 + y**2 + z'
        f = eval('lambda x, y, z : ' + code)

        with self.assertRaises(TypeError):
            IntExp(42)

        with self.assertRaises(ValueError):
            IntExp(f)

        f.code = code
        exp = IntExp(f)

        with self.assertRaises(RuntimeError):
            exp.compute({'x': 10, 'y': 9, 'foo': -1})

        with self.assertRaises(RuntimeError):
            exp.compute({'x': {}, 'y': [4, 5], 'z': -1})

        args = {'x': 243, 'y': 11, 'z': 8}

        result = exp.compute(args)
        self.assertEqual(result, f(**args))

    def test_data_exp(self):

        t_var = TermVar('foo')
        t_pair = TermPair('bar', TermVar('baz'))
        t_this = TermThis()
        t_var_zzz = TermVar('zzz')

        fcode = '10'
        f = eval('lambda: ' + fcode)
        f.code = fcode

        m_sm_10_exp = SegmentationMarkExp(IntExp(f))

        m_sm_10 = comm.SegmentationMark(10)
        m_sm_4 = comm.SegmentationMark(4)

        m_rec_empty = comm.Record()
        m_rec_12 = comm.Record({'1': 'one', '2': 'two'})
        m_rec_3 = comm.Record({'3': 'three'})

        m_rec_empty_exp = RecordExp(m_rec_empty.content)
        m_rec_12_exp = RecordExp(m_rec_12.content)
        m_rec_3_exp = RecordExp(m_rec_3.content)

        with self.assertRaises(TypeError):
            DataExp(42)

        with self.assertRaises(TypeError):
            DataExp('abc')

        with self.assertRaises(TypeError):
            DataExp([t_var, 'ololo'])

        with self.assertRaises(TypeError):
            DataExp([t_var, t_this], 42)

        # No init, terms: []
        dexp = DataExp([])
        result = dexp.compute({})

        self.assertIs(type(result), comm.Record)
        self.assertEqual(result.content, {})

        #---

        # Init: record, terms: []
        dexp = DataExp([], m_rec_12_exp)
        result = dexp.compute({})

        self.assertIs(type(result), comm.Record)
        self.assertEqual(result.content, {'1': 'one', '2': 'two'})

        #---

        # Init: record, terms: [records]
        dexp = DataExp([t_var, t_this], m_rec_empty_exp)
        result = dexp.compute({'__this__': m_rec_12, 'foo': m_rec_3})

        self.assertIs(type(result), comm.Record)
        self.assertEqual(result.content, {'1': 'one', '2': 'two', '3': 'three'})

        #---

        # Init: record, terms: [record, segmark]
        dexp = DataExp([t_var, t_this], m_rec_empty_exp)
        result = dexp.compute({'__this__': m_sm_4, 'foo': m_rec_3})

        self.assertIs(type(result), comm.Record)
        self.assertEqual(result.content, {'3': 'three', '__n__': 4})

        #---

        # Init: segmentation mark, terms: [records, segmark]
        dexp = DataExp([t_var, t_this, t_var_zzz], m_sm_10_exp)
        result = dexp.compute({'__this__': m_rec_12, 'foo': m_rec_3, 'zzz': m_sm_4})

        self.assertIs(type(result), comm.SegmentationMark)
        self.assertEqual(result.n, m_sm_10.n)

        (self.assertIn(i, result) for i in ('1', '2', '3'))

        #---

        # No init, terms: [records]
        dexp = DataExp([t_var, t_pair])
        result = dexp.compute({'baz': 100, 'foo': m_rec_3})

        self.assertIs(type(result), comm.Record)
        self.assertEqual(result.content, {'3': 'three', 'bar': 100})

        #---

        dexp = DataExp([t_var, t_this, t_var_zzz])

        # Non-record type in a union.
        with self.assertRaises(RuntimeError):
            dexp.compute({'__this__': m_sm_10, 'foo': 42, 'zzz': m_sm_4})

        # Two segmentation marks in a union.
        with self.assertRaises(RuntimeError):
            dexp.compute({'__this__': m_sm_10, 'foo': m_rec_3, 'zzz': m_sm_4})

        # No init, segmentation mark term
        result = dexp.compute({'__this__': m_rec_12, 'foo': m_rec_3, 'zzz': m_sm_4})

        self.assertIs(type(result), comm.SegmentationMark)
        self.assertEqual(result.n, m_sm_4.n)

        (self.assertIn(i, result) for i in ('1', '2', '3'))

    def test_record_exp(self):

        with self.assertRaises(TypeError):
            RecordExp(10)

        exp = RecordExp()
        result = exp.compute()
        self.assertIs(type(result), comm.Record)
        self.assertEqual(result.content, {})

        exp = RecordExp({'foo': 100})
        result = exp.compute()
        self.assertIs(type(result), comm.Record)
        self.assertEqual(result.content, {'foo': 100})

    def test_segmark_exp(self):

        with self.assertRaises(TypeError):
            SegmentationMarkExp(10)

        fcode = '5**2 - 23 + x'

        f = eval('lambda x: ' + fcode)
        f.code = fcode

        exp = SegmentationMarkExp(IntExp(f))
        result = exp.compute({'x': 4})
        self.assertIs(type(result), comm.SegmentationMark)
        self.assertEqual(result.n, f(4))
        self.assertEqual(result.content, {'__n__': f(4)})

        with self.assertRaises(RuntimeError):
            result = exp.compute({'x': -10})


if __name__ == '__main__':
    unittest.main()
