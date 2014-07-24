#!/usr/bin/env python3

from multiprocessing import Pool, Queue, Process, current_process, Event, Lock, TimeoutError
from time import sleep
import os
import sys
import random
from queue import Empty as Empty
import collections

def square(i):
    '1T'
    return i * i

def plus(i):
    '1T'
    return i + i

##############################################

class Box:

    def __init__(self, core, inputs, outputs):
        self.core = core
        self.inputs = inputs
        self.outputs = outputs

    def protocol(self):
        pass

    def handle_result(self):
        pass

##############################################

BoxResult = collections.namedtuple('BoxResult', 'data out_id')

in_task = Queue()
out_result = Queue()

def boxwrap(data, box):
    result = box.core(data)
    return BoxResult(result, box.out_id)

def pool_manager():
    pool = Pool(processes=4)

    def reg_result(res):
        out_result.put(res)

    while True:
        box, data = in_task.get()
        r = pool.apply_async(boxwrap, (data, box), callback=reg_result)

if __name__ == '__main__':
    #Box = collections.namedtuple('Box', 'core in_id out_id')

    channels = [collections.deque() for i in range(10)]
    channels[0].append(10)
    channels[0].append(100)

    boxes = [Box(square, 0, 1), Box(plus, 1, 2)]

    manager = Process(target=pool_manager)
    manager.start()

    while True:

        empty_channels = True

        for b in boxes:
            if len(channels[b.in_id]) > 0:
                m = channels[b.in_id].popleft()
                print("Input", b, m)
                in_task.put((b, m))

                empty_channels = False

        while True:
            try:
                res = out_result.get(block=empty_channels)
                empty_channels = False

                print("RES:", res)
                channels[res.out_id].append(res.data)

            except Empty:
                break

    manager.join()
    pool.close()
    pool.join()

    quit()
