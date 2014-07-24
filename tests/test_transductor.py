#!/usr/bin/env python3

# SLOPPY HACK
import sys, os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

import network as net
import unittest
import random
import components as comp
import communication as comm
import time
from multiprocessing import Process, Queue
import copy

class TestTransductor(unittest.TestCase):

    def test_segmark_barrier(self):

        output = Queue()

        def gen(inp):
            cont = copy.copy(inp)
            cont['ord'] += 1
            if inp['nseq'] == 0:
                return (None, None)
            cont['nseq'] -= 1
            return ({0: inp}, cont)

        def foo(m):
            acc = 0.
            m['n'] *= 10000
            r = random.random()
            for i in range(m['n']):
                acc += 0.0000001 * r
            return {0: m['ord']}

        def rsend(cid, msg):
            output.put(msg)

        init = []
        init.append(comm.DataMessage({'ord': 1, 'n': 500, 'nseq': 10}))
        init.append(comm.SegmentationMark(random.randint(1, 10)))
        init.append(comm.DataMessage({'ord': 100, 'n': 1, 'nseq': 10}))

        P = net.Network('')
        P.add_vertex("1P", "Generator", ['init'], ['values'], core=gen, initial_messages=init)
        P.add_vertex("1T", "Transductor", ['in'], ['out'], core=foo, n_cores=20)
        P.add_vertex("C1", "Printer", ['print'], [],  core=rsend)

        P.add_wire(('Generator',  0), ('Transductor', 0))
        P.add_wire(('Transductor', 0), ('Printer', 0))

        P.start()

        r = [0, 100]
        fail = None

        while True:
            msg = output.get()

            if msg.end_of_stream():
                break
            elif msg.is_segmark():
                r[0] += 100
                r[1] += 100
            else:
                i = msg.content
                if i not in range(*r):
                    fail = (i, r)

        self.assertEqual(fail, None)

if __name__ == '__main__':
    unittest.main()
