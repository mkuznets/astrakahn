#!/usr/bin/env python3

import sys
import os

# SLOPPY HACK
sys.path.insert(0, os.path.dirname(__file__) + '/..')

from boxes import PrimeTransductor, PrimeInductor

transductor = PrimeTransductor()
transductor.test()

inductor = PrimeInductor()
inductor.test()
