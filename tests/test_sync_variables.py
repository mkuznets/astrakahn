#!/usr/bin/env python3

import sys
sys.path[0:0] = ['..', '../..']


import re
import unittest
from components import Variable, Local, Const, StateInt, StateEnum, StoreVar
import communication as comm

class TestSyncVariables(unittest.TestCase):

    def test_variable(self):

        with self.assertRaises(TypeError):
            Variable({})

        v = Variable('foo')
        self.assertEqual(v.name, 'foo')
        self.assertEqual(v.get(), None)

        v.set('bar')
        self.assertEqual(v.get(), 'bar')

        d = {'1': 2}
        v.set(d)
        self.assertEqual(v.get(), d)
        self.assertEqual(id(v.get()), id(d))

        with self.assertRaises(NotImplementedError):
            repr(v)

    def test_local(self):

        v = Local('foo')

        d = {'1': 2}
        v.set(d)
        self.assertEqual(v.get(), d)
        self.assertEqual(id(v.get()), id(d))

        self.assertTrue(re.match('local\((.+?) \= (.+?)\)', repr(v)))

    def test_const(self):

        d = {'1': 2}
        v = Const('foo', d)

        with self.assertRaises(RuntimeError):
            v.set(d)

        self.assertEqual(v.get(), d)
        self.assertEqual(id(v.get()), id(d))

        self.assertTrue(re.match('const\((.+?) \= (.+?)\)', repr(v)))

    def test_state_int(self):

        with self.assertRaises(TypeError):
            StateInt('foo', '5')

        with self.assertRaises(ValueError):
            StateInt('foo', -5)

        #--
        # Default value.

        v = StateInt('foo', 8)
        self.assertEqual(v.get(), 0)

        #--
        # Non-default value.

        v = StateInt('foo', 8, 100)
        self.assertEqual(v.get(), 100)

        #--
        # Assignment type check.

        with self.assertRaises(TypeError):
            StateInt('foo', 8, '100')

        with self.assertRaises(TypeError):
            v.set('1000')

        #--
        # Range check.

        with self.assertRaises(RuntimeError):
            StateInt('foo', 8, 1090)

        with self.assertRaises(RuntimeError):
            v.set(-129)

        with self.assertRaises(RuntimeError):
            v.set(128)

        with self.assertRaises(RuntimeError):
            v.set(3412)

        try:
            for i in range(-128, 128):
                v.set(i)

        except Exception:
            self.fail('No range exception expected.')

        v.set(100)
        self.assertTrue(re.match('state\(int%d %s \= %d\)'
                                 % (8, 'foo', 100), repr(v)))

    def test_state_enum(self):

        with self.assertRaises(TypeError):
            StateEnum('foo', 'kkk')

        with self.assertRaises(ValueError):
            StateEnum('foo', [])

        with self.assertRaises(ValueError):
            StateEnum('foo', ['bar', 5])

        labels = ['A', 'B', 'C', 'D']

        #--
        # Default value

        v = StateEnum('foo', labels)
        self.assertEqual(v.get(), 0)

        #--
        # Non-default value

        v = StateEnum('foo', labels, 3)
        self.assertEqual(v.get(), 3)

        #--
        # Int assignment.

        v.set(1)
        self.assertEqual(v.get(), 1)

        with self.assertRaises(RuntimeError):
            StateEnum('foo', labels, 42)

        with self.assertRaises(RuntimeError):
            v.set(32)

        #--
        # Int assignment.

        v.set('C')
        self.assertEqual(v.get(), labels.index('C'))

        with self.assertRaises(RuntimeError):
            StateEnum('foo', labels, 'DD')

        with self.assertRaises(RuntimeError):
            v.set('DD')

        v.set(3)
        self.assertTrue(re.match('state\(enum %s \= %s\)'
                                 % ('foo', labels[3]), repr(v)))

    def test_store(self):

        v = StoreVar('foo')
        self.assertIs(v.get(), None)

        with self.assertRaises(TypeError):
            v.set({'1': 1})

        m = comm.Record({'foo': 'bar'})
        v.set(m)
        self.assertEqual(v.get(), m)
        self.assertEqual(id(v.get()), id(m))

        self.assertTrue(re.match('store\(%s \= (.+?)\)' % 'foo', repr(v)))


if __name__ == '__main__':
    unittest.main()
