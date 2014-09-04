#!/usr/bin/env python3

from multiprocessing import Pool, Queue, Process, current_process, Event, Lock, TimeoutError
import multiprocessing
from time import sleep
import os
import sys
import random
from queue import Empty as Empty

### Generate input messages #######

def gen(queue):

    for i in range(5000):
        #if i > 1 and not (i % 10):
            #sleep(random.random() * 2)
        queue.put((i, i+1))
        print("Put:", i)
        sleep(2)
    queue.put(None)

#####################################

class Worker(object):

    def __init__(self, i):
        self.i = 0
        self.cq = Queue()
        self.exec_tasks = dict()

    def protocol(self, i):
        self.i = i

        while True:
            while True:
                try:
                    # Wait for a message if there're no ready tasks
                    block = False if self.exec_tasks else True

                    cm = self.cq.get(block)
                    (task_id, task_priority) = cm

                    # Dequeue task
                    if task_priority == 0 and task_id in self.exec_tasks:
                        del self.exec_tasks[task_id]

                    elif task_priority > 0:
                        self.exec_tasks[task_id] = {'obj': all_tasks[task_id],
                                                    'priority': task_priority,
                                                    'state': 'ready'}

                except Empty:
                    break

            # Check for blocked tasks
            for (task_id, task) in self.exec_tasks.items():
                if task['state'] == 'blocked_in':
                    if task['obj'].input_channel.e.is_set():
                        task['state'] = 'ready'
                elif task['state'] == 'blocked_out':
                    if not task['obj'].output_channel.f.is_set():
                        task['state'] = 'ready'

            print(os.getpid(), self.exec_tasks)

            # Get a new task to run with respect to their priorities.
            priorities = {}
            start = 0
            for (task_id, task) in self.exec_tasks.items():
                if task['state'] == 'ready' or task['state'] == 'paused':
                    p = task['priority']
                    priorities[task_id] = range(start, start + p)
                    start += p

            if start == 0:
                print("start == 0")
                continue

            max_rand = start - 1
            rand = random.randint(0, max_rand)

            task_run = None
            for (task_id, r) in priorities.items():
                if rand in r:
                    task_run = task_id

            assert(task_run is not None)

            task_run_obj = self.exec_tasks[task_run]['obj']

            r = task_run_obj.protocol()
            self.exec_tasks[task_run]['state'] = r
            print("Set new state to", task_run, ":", r)


class Channel:
    def __init__(self, capacity):
        self.q = Queue()
        self.e = Event()
        self.f = Event()
        self.e.clear()
        self.f.set()
        self.c = capacity

    def get(self, block=True):
        s = self.q.qsize()

        m = self.q.get(block)

        if self.q.qsize() == 0:
            self.e.clear()

        if s == self.c:
            self.f.set()

        return m

    def put(self, m):
        self.f.wait()
        s = self.q.qsize()
        self.q.put(m)

        if self.q.qsize() == self.c:
            self.f.clear()

        if s == 0:
            self.e.set()


class FooBox:

    def __init__(self):
        self.input_channel = Channel(10)
        self.output_channel = Channel(10)

    def protocol(self):
        while True:
            try:
                self.input_channel.e.wait()
                m = self.input_channel.get(False)
            except Empty:
                return 'blocked_in'

            print(m)
            try:
                result = self.core(m[0], m[1])
                self.output_channel.put(result)
            except Empty:
                return 'blocked_out'

            return 'paused'

class BoxCalc(FooBox):
    def core(self, a, b):
        return (a + b, a * b)

class BoxPlus(FooBox):
    def core(self, a, b):
        return (a + b, 0)


if __name__ == "__main__":

    manager = multiprocessing.Manager()

    n_workers = 2
    workers = []
    workers_threads = []

    all_tasks = {}
    all_tasks['calc'] = BoxCalc()
    all_tasks['plus'] = BoxPlus()
    all_tasks['calc'].output_channel = all_tasks['plus'].input_channel

    for i in range(n_workers):
        w = Worker(i)
        w_thread = Process(target=w.protocol, args=(i,))
        workers.append(w)
        workers_threads.append(w_thread)

    # Input generator
    thread = Process(target=gen, args=(all_tasks['calc'].input_channel,))
    thread.start()

    workers[0].cq.put(('calc', {'state': 'ready', 'priority': 1}))
    workers[1].cq.put(('plus', {'state': 'ready', 'priority': 1}))


    for w in workers_threads:
        w.start()

    while True:
        print("Output:", all_tasks['plus'].output_channel.get())

    for w in workers_threads:
        w.join()
