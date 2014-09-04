#!/usr/bin/env python3

# SLOPPY HACK
import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

import components as comp
import communication as comm
import time
from multiprocessing import Process
import random
import copy


def gen(inp):
    """
    Generate prime numbers
    """

    continuation = copy.copy(inp)
    continuation['start'] += 1

    if inp['n'] == 0:
        return (None, None)

    continuation['n'] -= 1

    return ({0: inp['start']}, continuation)

# Box definition
box = comp.Generator(n_inputs=1, n_outputs=1, core=gen,
                     initial_messages=[comm.DataMessage({'start': 1, 'n': 20})])

ch_gen = comm.Channel()
ch_out = comm.Channel()

box.set_input(0, ch_gen)
box.set_output(0, ch_out)

box.start()

while True:
    r = ch_out.get()
    print(r)
    if r.is_segmark():
        break

box.join()
