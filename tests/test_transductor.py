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


def foo(a):
    st = time.time()
    acc = 0.
    b = 5000000
    for i in range(b):
        acc += 0.0000001 * a

    end = time.time()
    return ((a, acc), st, end)


def gen(channel):

    for i in range(300):
        channel.wait_blocked()
        if i > 1 and not (i % 10):
            channel.put(comm.SegmentationMark(random.randint(1, 10)))
            continue
            #sleep(random.random() * 2)
        channel.put(comm.DataMessage(i))

    channel.put(comm.SegmentationMark(0))

# Box definition
box = comp.Transductor(1, 1, foo, 10)

ch_gen = comm.Channel(box.input_ready)
ch_out = comm.Channel()

box.set_input(0, ch_gen)
box.set_output(0, ch_out)

# Input generator
thread = Process(target=gen, args=(ch_gen,))
thread.start()

box.start()

box.join()
