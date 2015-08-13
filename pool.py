#!/usr/bin/env python3

from multiprocessing import Process, Pool, Array, Queue
import collections

import os
import marshal
import types
import time

import communication as comm

Result = collections.namedtuple('Result',
                                'vertex_id action dispatch aux_data tm')

def core_wrapper(core, task_data, timestp):

    tlaunch = time.time() - timestp

    code = marshal.loads(core[1])
    core = types.FunctionType(code, globals(), core[0])

    vertex_id = task_data['vertex_id']
    args = task_data['args']

    #print(os.getpid(), args[0].keys(), core.__name__)

    st = time.time()
    output = core(*args)
    timecore = time.time() - st

    if output is None:
        return Result(vertex_id, '', {}, None, (timestp, timecore, tlaunch, time.time()))

    else:
        action, dispatch, aux_data = output

        dispatch = {p: [comm.Record(msg) for msg in stream]
                    for p, stream in dispatch.items()}

        return Result(vertex_id, action, dispatch, aux_data, (timestp, timecore, tlaunch, time.time()))

def print_error(err):
    print("Error in pool:", err)


class PoolManager:

    def __init__(self, nproc):
        self.nproc = nproc
        self.in_queue = Queue()
        self.out_queue = Queue()

        self.pm = Process(target=self.manager)

        self.obj_id = 0

    def start(self):
        self.pm.start()

    def finish(self):
        self.pm.join()

    def dispatch_result(self, result):
        ot = time.time() - result.tm[0]
        print(result.vertex_id, "\t", '%07f' % ot, "\t"

              "\t", '%06.2f%%' % (result.tm[1]/ot * 100),
              "\t", '%06.2f%%' % (result.tm[2]/ot * 100),
              "\t", '%06.2f%%' % ((time.time() - result.tm[3])/ot * 100)
        )

        self.out_queue.put(result)

    def enqueue(self, core, task_data):
        name = core.__name__
        core_serialized = (name, marshal.dumps(core.__code__))
        self.in_queue.put((core_serialized, task_data))

    def manager(self):

        pool = Pool(processes=self.nproc, )

        while True:
            task = self.in_queue.get()
            ttask = task + (time.time(), )
            pool.apply_async(core_wrapper, ttask, callback=self.dispatch_result,
                             error_callback=print_error)

        pool.close()
        pool.join()
