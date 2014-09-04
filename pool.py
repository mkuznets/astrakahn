#!/usr/bin/env python3

from multiprocessing import Process, Pool, Array, Queue
import collections

# For shared arrays
import ctypes

import marshal
import types

import data_objects as data

Result = collections.namedtuple('Result',
                                'vertex_id action out_mapping aux_data')


def core_wrapper(core, task_data):

    code = marshal.loads(core[1])
    core = types.FunctionType(code, globals(), core[0])

    vertex_id = task_data['vertex_id']
    args = task_data['args']

    # Get the objects by their references.
    # TODO: iterate over each arguments indead of the list of them.
    for i in range(len(args)):
        if type(args[i]) == data.ref:
            args[i] = data.obj(args[i], data.to_numpy(args[i]))

    action, out_mapping, aux_data = core(*args)

    return Result(vertex_id, action, out_mapping, aux_data)


class PoolManager:

    def __init__(self, nproc):
        self.nproc = nproc
        self.in_queue = Queue()
        self.out_queue = Queue()

        self.pm = Process(target=self.manager)

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
        pool = Pool(processes=self.nproc)

        while True:
            task = self.in_queue.get()
            pool.apply_async(core_wrapper, task, callback=self.dispatch_result)

        pool.close()
        pool.join()

###########################

# Box functions


def foo(obj, n):
    array = obj.data
    array[:] = n
    return obj.ref

###########################

if __name__ == '__main__':

    shared_array = Array(ctypes.c_double, 100)
    data.new('array', shared_array)

    pm = PoolManager(4)
    pm.start()

    pm.enqueue(foo, {'vertex_id': 2, 'args': [data.ref('array'), 12]})
