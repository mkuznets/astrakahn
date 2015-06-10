#!/usr/bin/env python3

from multiprocessing import Process, Pool, Array, Queue
import collections

import os
import marshal
import types

import communication as comm

Result = collections.namedtuple('Result',
                                'vertex_id action dispatch aux_data')

def core_wrapper(core, task_data):

    code = marshal.loads(core[1])
    core = types.FunctionType(code, globals(), core[0])

    vertex_id = task_data['vertex_id']
    args = task_data['args']

    output = core(*args)

    if output is None:
        return Result(vertex_id, '', {}, None)

    else:
        action, dispatch, aux_data = output

        dispatch = {p: [comm.Record(msg) for msg in stream]
                    for p, stream in dispatch.items()}

        return Result(vertex_id, action, dispatch, aux_data)

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
        self.out_queue.put(result)

    def enqueue(self, core, task_data):
        name = core.__name__
        core_serialized = (name, marshal.dumps(core.__code__))
        self.in_queue.put((core_serialized, task_data))

    def manager(self):

        pool = Pool(processes=self.nproc, )

        while True:
            task = self.in_queue.get()
            pool.apply_async(core_wrapper, task, callback=self.dispatch_result,
                             error_callback=print_error)

        pool.close()
        pool.join()
