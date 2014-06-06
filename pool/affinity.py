#!/usr/bin/env python3

from multiprocessing import Pool, Queue, Process, current_process, Event, Lock, TimeoutError
import time
import os
import sys
import random
from queue import Empty as Empty
from collections import deque

### Parameters

cq = Queue()  # control queue

n_workers = 1
n_cores = 0
max_cores = n_workers


### Generate input messages #######

def gen(queue):

    for i in range(100):
        #if i > 1 and not (i % 10):
            #sleep(random.random() * 2)
        queue.put((0, i))
        #sleep(2)
    queue.put(None)

#####################################

def calc(a):
    acc = 0.
    b = 2000000
    for i in range(b):
        acc += 0.0000001 * a
    return (1, (a, acc))

### Pool of workers

def worker(q):
    while True:
        m = q.get()
        if m is None:
            break

        #print('[' + str(os.getpid()) + '] ' "Assigned", m)
        r = calc(m)
        cq.put(r)

w = {}
wq = [Queue() for i in range(n_workers)]
pids = []
for i in range(n_workers):
    w[i] = Process(target=worker, args=(wq[i],))
    w[i].start()
    pids.append(w[i].pid)

print(pids)
input("Pin these PIDs to cores")

time_start = time.time()

### Coordinator

rr = 0

generator = Process(target=gen, args=(cq,))
generator.start()

msgs = deque()

assigned = 0
finalise = False

while True:
    try:
        c = cq.get()
        if c is None:
            finalise = True
            #print("countdown")
        else:
            if c[0] == 0:
                if n_cores < max_cores:
                    wq[rr].put(c[1])
                    n_cores += 1
                    rr = (rr + 1) % n_workers
                else:
                    msgs.append(c[1])
            elif c[0] == 1:
                n_cores -= 1
                print('Result', c[1])

                if len(msgs) == 0 and n_cores == 0 and finalise:
                    for q in wq:
                        q.put(None)
                    break

                elif len(msgs) > 0:
                    m = msgs.popleft()
                    wq[rr].put(m)
                    n_cores += 1
                    rr = (rr + 1) % n_workers

    except Empty:
        break

for i in range(n_workers):
    w[i].join()

time_end = time.time()

print("Time:", time_end - time_start)

#####################################
