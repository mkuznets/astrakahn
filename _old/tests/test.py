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
import sync

cid = 1

def gen(channels):
    global cid

    for i in range(300):
        cid = (cid + 1) % len(channels)
        #cid = random.randint(0, len(channels)-1)

        #channels[cid].wait_blocked()
        channels[cid].put(comm.DataMessage(i))
        #time.sleep(0.4)

# Box definition
box = comp.Synchroniser(2, 1, sync.zip2, sync.variables)

ch_a = comm.Channel()
ch_b = comm.Channel()
ch_c = comm.Channel()

box.set_input(0, ch_a)
box.set_input(1, ch_b)
box.set_output(0, ch_c)

# Input generator
thread = Process(target=gen, args=([ch_a, ch_b],))
thread.start()

box.start()
box.join()
