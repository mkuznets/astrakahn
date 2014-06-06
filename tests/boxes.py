#!/usr/bin/env python3

import sys
import os
from copy import copy
import math

# SLOPPY HACK
sys.path.insert(0, os.path.dirname(__file__) + '/..')

from communication import SegmentationMark
from components import Transductor, Inductor, Reductor, Copier, Synchroniser
from helpers import Testable

import sync


class PrimeTransductor(Testable):

    def __init__(self):

        self.type = Transductor

        self.passport = {
            'input':  (int,),
            'output': (int,)
        }

        self.test_input = list(range(50)) + [SegmentationMark(2)] \
            + list(range(50, 75)) + [SegmentationMark(0)] \
            + list(range(75, 100))

        self.reference_output = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37,
                                 41, 43, 47, '))((', 53, 59, 61, 67, 71, 73,
                                 'sigma_0']

    def function(self, input):

        n = copy(input)

        if n < 2:
            return None
        if n == 2:
            return {0: n}
        if not (n % 2):
            return None

        bound = math.sqrt(n)
        for i in range(3, int(bound)+1, 2):
            if not (n % i):
                return None
        return {0: n}


class PrimeInductor(Testable):

    def __init__(self):

        self.type = Inductor

        self.test_input = [{'low': 200, 'n_primes': 3},
                           SegmentationMark(2),
                           {'low': 1000, 'n_primes': 3},
                           {'low': 321, 'n_primes': 3},
                           SegmentationMark(0),
                           {'low': 321, 'n_primes': 40}]

        self.reference_output = [211, 223, 227, ')))(((', 1009, 1013, 1019,
                                 ')(', 331, 337, 347, 'sigma_0']

        self.passport = {
            'input':  ({'low': int, 'n_primes': int},),
            'output': (int,)
        }

    def function(self, input):
        """
        Generate prime numbers
        """

        input_data = copy(input)
        n = input_data['low']
        n_primes = input_data['n_primes']

        if n_primes == 0:
            return {}

        continuation = {'low': n+1, 'n_primes': n_primes}

        if n < 2:
            return {'continuation': continuation}
        if n == 2:
            continuation['n_primes'] -= 1
            return {0: n, 'continuation': continuation}
        if not (n % 2):
            return {'continuation': continuation}

        bound = math.sqrt(n)
        for i in range(3, int(bound)+1, 2):
            if not (n % i):
                return {'continuation': continuation}

        continuation['n_primes'] -= 1

        return {0: n, 'continuation': continuation}


class SomeReductor(Testable):

    def __init__(self):

        self.type = Reductor

        self.passport = {
            'input':  (int, int,),
            'output': (int,)
        }

        self.test_input = \
            {0: [2, 1, SegmentationMark(1), 2, SegmentationMark(0)],
             1: [0, 1, 0, SegmentationMark(2), 1, 1, 1, SegmentationMark(1),
                 0, 0, 1, SegmentationMark(0)]
             }

        self.reference_output = \
            [3, ')(', 0, 3, 'sigma_0']

    def function(self, input_a, input_b):

        a = copy(input_a)
        b = copy(input_b)

        result = (a + b) % 4

        return {0: result}

class MonadicReductor(Testable):

    def __init__(self):

        self.type = Reductor

        self.passport = {
            'input':  (int,),
            'output': (int,)
        }

        self.test_input = [2, 0, 1, 0, SegmentationMark(1),
                           1, 1, 1, 1, SegmentationMark(1),
                           2, 0, 0, 1, SegmentationMark(0)]

        self.reference_output = \
            [3, 0, 3, 'sigma_0']

    def function(self, input_a, input_b):

        a = copy(input_a)
        b = copy(input_b)

        result = (a + b) % 4

        return {0: result}


class Merger(Testable):

    def __init__(self):

        self.type = Copier

        self.passport = {
            'input':  (int, int,),
            'output': (int,)
        }

        self.test_input = \
            {0: [1, 2, 3, 4, SegmentationMark(0), 10],
             1: [7, 8, 9, 10, 9, SegmentationMark(0)]
            }

        self.reference_output = \
            [3, ')(', 0, 3, 'sigma_0']

    def function(self, input_a, input_b):

        a = copy(input_a)
        b = copy(input_b)

        result = (a + b) % 4

        return {0: result}

class Sync_zip2(Testable):

    def __init__(self):

        self.type = Synchroniser
        self.function = sync.zip2

        self.passport = {
            'input':  (object, object,),
            'output': (object,)
        }

        self.test_input = \
            {0: [1, 2, 3, 4, SegmentationMark(0), 10],
             1: [7, 8, 9, 10, 9, SegmentationMark(0)]
            }

        self.reference_output = \
            [3, ')(', 0, 3, 'sigma_0']
