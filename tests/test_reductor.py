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

    continuation = copy.copy(inp)
    continuation['start'] += 1

    if inp['n'] == 0:
        return (None, None)

    continuation['n'] -= 1

    return ({0: inp['start']}, continuation)

def red(a, b):
    return {0: a + b}

def rprint(cid, msg):
    print(str(cid) + ":", msg)

# Box definition
box_gen = comp.Producer(n_inputs=1, n_outputs=1, core=gen,
                         initial_messages=[comm.DataMessage({'start': 1, 'n': 20}),
                                           comm.SegmentationMark(1),
                                           comm.DataMessage({'start': 1, 'n': 30}),
                                           #comm.SegmentationMark(2),
                                           #comm.DataMessage({'start': 1, 'n': 1000}),
                                           ])

box_reductor = comp.Reductor(n_inputs=1, n_outputs=2, core=red, n_cores=10,
                              ordered=False, segmentable=True)

box_consumer = comp.Consumer(n_inputs=2, core=rprint)

global_input= comm.Channel()
to_reductor = comm.Channel()
global_output = comm.Channel()
global_secondary = comm.Channel()

box_gen.set_input(0, global_input)
box_gen.set_output(0, to_reductor)

box_reductor.set_input(0, to_reductor)
box_reductor.set_output(0, global_output)
box_reductor.set_output(1, global_secondary)

box_consumer.set_input(0, global_output)
box_consumer.set_input(1, global_secondary)

box_reductor.start()
box_gen.start()
box_consumer.start()

box_gen.join()
box_reductor.join()
box_consumer.join()
