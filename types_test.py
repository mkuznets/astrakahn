#!/usr/bin/env python3

from random import random, randint, shuffle
from msg_types import Msg
import unittest


gen_rint = lambda: randint(10, 100000)
gen_rfloat = lambda: 10000 * random()

class TestTypeSystem(unittest.TestCase):

    def test_elementary(self):
        rint = gen_rint()
        rfloat = gen_rfloat()

        # Check for correct elementary messages
        out_float = Msg.unpack_message(float, rfloat)
        self.assertEqual(out_float, rfloat)

        out_int = Msg.unpack_message(int, rint)
        self.assertEqual(out_int, rint)

        # Wring type of message
        with self.assertRaises(AssertionError):
            Msg.unpack_message(float, rint)
        with self.assertRaises(AssertionError):
            Msg.unpack_message(int, rfloat)
        with self.assertRaises(AssertionError):
            Msg.unpack_message(float, [rfloat])

    def test_typle(self):

        def gen_data(rand_function, correct_type, wrong_type):
            n = randint(10, 20)

            data = tuple([rand_function() for i in range(n)])
            ok = tuple([type(x) for x in data])

            # Additional element in passport
            fail_1 = tuple(list(ok) + [wrong_type])
            # Lack of elements
            fail_2 = tuple(list(ok)[:-1])
            # Wrong type of an element
            fail_3 = tuple(list(ok)[:-1] + [wrong_type])

            return (data, ok, fail_1, fail_2, fail_3)

        (rint_tuple,
         rint_tuple_pass_ok,
         rint_tuple_pass_fail_1,
         rint_tuple_pass_fail_2,
         rint_tuple_pass_fail_3) = gen_data(gen_rint, int, float)

        (rfloat_tuple,
         rfloat_tuple_pass_ok,
         rfloat_tuple_pass_fail_1,
         rfloat_tuple_pass_fail_2,
         rfloat_tuple_pass_fail_3) = gen_data(gen_rfloat, float, int)


        self.assertEqual(Msg.unpack_message(rint_tuple_pass_ok, rint_tuple),
                         rint_tuple)
        self.assertEqual(Msg.unpack_message(rfloat_tuple_pass_ok, rfloat_tuple),
                         rfloat_tuple)

        # elementary type instead of compound one
        with self.assertRaises(AssertionError):
            Msg.unpack_message((int, float), gen_rint())
        with self.assertRaises(AssertionError):
            Msg.unpack_message((int, float), gen_rint())

        # int failures
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rint_tuple_pass_fail_1, rint_tuple)
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rint_tuple_pass_fail_2, rint_tuple)
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rint_tuple_pass_fail_3, rint_tuple)

        # float failures
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rfloat_tuple_pass_fail_1, rfloat_tuple)
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rfloat_tuple_pass_fail_2, rfloat_tuple)
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rfloat_tuple_pass_fail_3, rfloat_tuple)

    def test_list(self):

        def gen_data(rand_function, correct_type, wrong_type):
            n = randint(10, 20)

            data = [rand_function() for i in range(n)]
            ok_1 = [type(x) for x in data]
            # List-term matches longer lists
            ok_2 = ok_1[:-3]
            # Wildcard
            ok_3 = ok_1[:-5] + [object]

            # Additional element in passport
            fail_1 = ok_1 + [wrong_type]
            # Wrong type of an element
            fail_2 = ok_1[:-1] + [wrong_type]

            return (n, data, ok_1, ok_2, ok_3, fail_1, fail_2)

        (n,
         rint_list,
         rint_list_pass_ok_1,
         rint_list_pass_ok_2,
         rint_list_pass_ok_3,
         rint_list_pass_fail_1,
         rint_list_pass_fail_2) = gen_data(gen_rint, int, float)

        (n,
         rfloat_list,
         rfloat_list_pass_ok_1,
         rfloat_list_pass_ok_2,
         rfloat_list_pass_ok_3,
         rfloat_list_pass_fail_1,
         rfloat_list_pass_fail_2) = gen_data(gen_rfloat, float, int)

        self.assertEqual(Msg.unpack_message(rint_list_pass_ok_1, rint_list),
                         rint_list)
        self.assertEqual(Msg.unpack_message(rfloat_list_pass_ok_1, rfloat_list),
                         rfloat_list)
        self.assertEqual(Msg.unpack_message(rint_list_pass_ok_2, rint_list),
                         rint_list[:-3])
        self.assertEqual(Msg.unpack_message(rfloat_list_pass_ok_2, rfloat_list),
                         rfloat_list[:-3])
        self.assertEqual(Msg.unpack_message(rint_list_pass_ok_3, rint_list),
                         rint_list[:-5] + [rint_list[-5:]])
        self.assertEqual(Msg.unpack_message(rfloat_list_pass_ok_3, rfloat_list),
                         rfloat_list[:-5] + [rfloat_list[-5:]])

        # elementary type instead of compound one
        with self.assertRaises(AssertionError):
            Msg.unpack_message([int, float], gen_rint())
        with self.assertRaises(AssertionError):
            Msg.unpack_message([int, float], gen_rint())

        # int failures
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rint_list_pass_fail_1, rint_list)
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rint_list_pass_fail_2, rint_list)

        # float failures
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rfloat_list_pass_fail_1, rfloat_list)
        with self.assertRaises(AssertionError):
            Msg.unpack_message(rfloat_list_pass_fail_2, rfloat_list)


if __name__ == '__main__':
    unittest.main()
