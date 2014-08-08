#!/usr/bin/env python3

from multiprocessing import Process, Pool, Array, Queue
import collections
import time

# For shared arrays
import ctypes
import numpy as np

import data_objects as data

Task = collections.namedtuple('Task', 'core args')
Result = collections.namedtuple('Result', 'action data')


def core_wrapper(core, task_data):

    vertex_id = task_data['vertex_id']
    args = task_data['args']

    # Get the objects by their references.
    # TODO: iterate over each arguments indead of the list of them.
    for i in range(len(args)):
        if type(args[i]) == data.ref:
            args[i] = data.obj(args[i], data.to_numpy(args[i]))

    result = core(*args)

    return result


class PoolManager:

    def __init__(self, nproc):
        self.nproc = nproc
        self.in_queue = Queue()
        self.out_queue = Queue()

        self.pm = Process(target=self.manager)

    def start(self):
        self.pm.start()

    def dispatch_result(self, result):
        self.out_queue.put(result)

    def enqueue(self, core, task_data):
        self.in_queue.put(Task(core, task_data))

    def manager(self):
        pool = Pool(processes=self.nproc)

        while True:
            task = self.in_queue.get()
            if type(task) != Task:
                raise ValueError('Pool: wrong format of task.')

            r = pool.apply_async(core_wrapper, task, callback=self.dispatch_result)

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