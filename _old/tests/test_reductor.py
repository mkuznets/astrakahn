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
import network as net

def gen(inp):

    continuation = copy.copy(inp)
    continuation['start'] += 1

    if inp['n'] == 0:
        return (None, None)

    continuation['n'] -= 1

    return ({0: inp['start']}, continuation)

def summator(a, b):
    return {0: a + b}

def rprint(cid, msg):
    print(str(cid) + ":", msg)


init = [comm.DataMessage({'start': 1, 'n': 20}),
        comm.SegmentationMark(1),
        comm.DataMessage({'start': 1, 'n': 30}),
        comm.SegmentationMark(2),
        comm.DataMessage({'start': 1, 'n': 1000}),
        ]

P = net.Network("test_reductor")

P.add_vertex("1P", "Generator", ['init'], ['values'],  gen, {'initial_messages': init})
P.add_vertex("2MU", "Reductor", ['in'], ['a', 'b'],  summator, {'n_cores': 2})
P.add_vertex("C2", "Printer", ['printa', 'printb'], [],  rprint)

P.wire(('Generator', 'values'), ('Reductor', 'in'))
P.wire(('Reductor', 'a'), ('Printer', 'printa'))
P.wire(('Reductor', 'b'), ('Printer', 'printb'))

P.start()
P.join()

P.debug_status()
