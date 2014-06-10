#!/usr/bin/env python3

from multiprocessing import Queue, Process, Event, Array
from queue import Empty as Empty

import os
import ctypes
import numpy as np
import random

### Generate input messages #######

shared_array_base = Array(ctypes.c_double, 100)
shared_array = np.ctypeslib.as_array(shared_array_base.get_obj())

def gen(queue):

    for i in range(0, 100, 2):
        #if i > 1 and not (i % 10):
            #sleep(random.random() * 2)
        queue.put(i)
        #sleep(2)
    queue.put(None)

#####################################

class Channel:
    def __init__(self, capacity):

        ### Shared valiabled
        self.q = Queue()

        self.nonempty = Event()
        self.nonempty.clear()

        self.notfull = Event()
        self.notfull.set()

        self.input_ready = None  # Common for all inputs of a box
        ###

        self.c = capacity

    def get(self, block=True, timeout=None):
        n = self.q.qsize()

        m = self.q.get(block=block, timeout=timeout)

        if self.q.qsize() == 0:
            self.nonempty.clear()
            if self.input_ready is not None:
                self.input_ready.clear()

        if n == self.c:
            self.notfull.set()

        return m

    def put(self, m, block=True, timeout=None):
        n = self.q.qsize()

        self.q.put(obj=m, block=block, timeout=timeout)

        if self.q.qsize() == self.c:
            self.notfull.clear()

        if n == 0:
            self.nonempty.set()
            if self.input_ready is not None:
                self.input_ready.set()

class Box:

    def __init__(self):
        self.input_ready = Event()
        self.input_ready.clear()

        self.input_channels = {}
        self.output_channels = {}

        self.input_channels[0] = Channel(10)
        self.input_channels[0].input_ready = self.input_ready
        self.output_channels[0] = Channel(10)

        self.n_workers = 10
        self.workers = {}
        self.workers_threads = {}

        self.core = None

        self.input_buffers = [Queue() for i in range(10)]
        self.output_buffer = Queue()

        self.feedback = Queue()

    def core_worker(self, cid):
        q = self.input_buffers[cid]
        while True:
            m = q.get()
            if m is None:
                self.output_buffer.put((cid, None,))
                break
            result = self.core(m)

            self.output_buffer.put((cid, result,))

    def router(self):
        final = False

        while True:

            while True:
                try:
                    c = self.feedback.get(block=final)

                    if self.workers[c] == 0:
                        del self.workers[c]
                    else:
                        self.workers[c] -= 1

                    if final and len(self.workers.keys()) == 0:
                        self.output_buffer.put((-1, None))
                        return

                except Empty:
                    break

            n_active_workers = len(self.workers.keys())

            if n_active_workers < self.n_workers:
                # Create core workers
                for i in range(self.n_workers - n_active_workers):
                    self.workers[i] = 0
                    self.workers_threads[i] = Process(target=self.core_worker, args=(i,))
                    self.workers_threads[i].start()

            #self.input_channels[0].nonempty.wait()
            m = self.input_channels[0].get()

            if m is None:
                for c in self.workers.keys():
                    self.input_buffers[c].put(m)
                final = True
                continue

            w = sorted(self.workers, key=self.workers.get)[0]

            self.input_buffers[w].put(m)
            self.workers[w] += 1

    def merger(self):
        while True:
            # Wait for outputs availability
            for (ch_id, ch) in self.output_channels.items():
                ch.notfull.wait()
            cid, m = self.output_buffer.get()

            if cid < 0 and m is None:
                return

            #print("Output:", cid, m)
            self.feedback.put(cid)

def foo(a):
    k = shared_array[a:a+2]

    print(os.getpid(), shared_array.__array_interface__['data'])

    k[0] = random.random()
    k[1] = float(os.getpid())
    return 3

    #acc = 0.
    #b = 2000000
    #for i in range(b):
    #    acc += 0.0000001 * a
    #return acc

if __name__ == "__main__":

    # Box definition
    box = Box()
    box.core = foo


    # Input generator
    thread = Process(target=gen, args=(box.input_channels[0],))
    thread.start()

    router = Process(target=box.router)
    router.start()
    merger = Process(target=box.merger)
    merger.start()

    router.join()
    merger.join()

