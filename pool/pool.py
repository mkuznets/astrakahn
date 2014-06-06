#!/usr/bin/env python3

from multiprocessing import Pool, Queue, Process, current_process, Event, Lock, TimeoutError
from time import sleep
import os
import sys
import random
from queue import Empty as Empty

max_n_init = int(sys.argv[1])
max_n = max_n_init
n = 0

pid = 0

queue = Queue()
result_queue = Queue()
update = Event()
update.clear()
lock = Lock()

stop = Event()
stop.clear()

#### Generate input messages #######

def gen():
    global queue

    for i in range(5000):
        #if i > 1 and not (i % 10):
            #sleep(random.random() * 2)
        queue.put(i)
    queue.put(None)

thread = Process(target=gen)
thread.start()

#####################################

def worker_exit(i):
    global n, update, lock

    #print(i[0], "stopped")

    lock.acquire()
    n -= 1
    update.set()
    lock.release()

def worker(i):
    global queue, result_queue, stop

    cnt = 0

    while True:
        try:
            num = queue.get(timeout=1)
            cnt += 1

            if num is None:
                stop.set()

            else:
                #print(i, num)

                r = 0.0
                for k in range(100000):
                    r += num * 0.00001 * k

        except Empty:
            print("Stat", i, cnt)
            return i

        if stop.is_set() and i != 1:
            print("Stat", i, cnt)
            return i

def enqueue_worker():
    global max_n, n, queue, lock, pid

    while n < max_n:
        lock.acquire()
        n += 1
        pid += 1
        #print("New pid: ", pid)
        lock.release()

        yield pid

def foo(a):
    return a * a

class b:
    def __init__(self):
        self.f = foo

    def reg(self, r):
        print(r)

bb = b()

pool = Pool(processes=4)
pool.map_async(bb.f, [1, 2, 3, 4, 5], 1, bb.reg)


pool.close()
pool.join()

quit()

while True:
    task_iter = enqueue_worker()
    for x in task_iter:
        pool.map_async(b.f, [1, 2, 3, 4, 5], 1, worker_exit)


    max_n = min(queue.qsize(), max_n_init) #random.randint(1, 10)
    update.wait()

    if stop.is_set():
        pool.terminate()
        break

    update.clear()

pool.close()
pool.join()
#print("End")
