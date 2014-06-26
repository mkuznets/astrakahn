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

def rprint(cid, msg):
    print(str(cid) + ":", msg)


init = [comm.DataMessage({'start': 1, 'n': 20}),
        comm.SegmentationMark(1),
        comm.DataMessage({'start': 1, 'n': 30}),
        comm.SegmentationMark(2),
        comm.DataMessage({'start': 1, 'n': 1000}),
        ]

P = net.Network("test_reductor")

P.add_vertex("1P", "G", ['init'], ['values'],  gen, {'initial_messages': init})
P.add_vertex("3R1", "R", ['in'], ['a', 'b', 'c'])
P.add_vertex("C3", "P", ['pa', 'pb', 'pc'], [],  rprint)

P.wire(('G', 'values'), ('R', 'in'))
P.wire(('R', 'a'), ('P', 'pa'))
P.wire(('R', 'b'), ('P', 'pb'))
P.wire(('R', 'c'), ('P', 'pc'))

P.start()
P.join()

P.debug_status()
