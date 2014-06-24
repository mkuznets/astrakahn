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

def foo(a):
    st = time.time()
    acc = 0.
    b = 5000000
    for i in range(b):
        acc += 0.0000001 * a

    end = time.time()
    return {0: ((a, acc), st, end)}

def rprint(cid, msg):
    print(str(cid) + ":", msg)

init = []
for i in range(0, 30, 10):
    init.append(comm.DataMessage({'start': i, 'n': 10}))
    init.append(comm.SegmentationMark(random.randint(1, 10)))

P = net.Network("test_transductor")

P.add_vertex("1P", "Generator", ['init'], ['values'],  gen, {'initial_messages': init})
P.add_vertex("1T", "Transductor", ['in'], ['out'],  foo, {'n_cores': 1})
P.add_vertex("C1", "Printer", ['print'], [],  rprint)

P.wire(('Generator', 'values'), ('Transductor', 'in'))
P.wire(('Transductor', 'out'), ('Printer', 'print'))

P.start()
P.join()
