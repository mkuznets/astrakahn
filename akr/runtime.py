from collections import deque, Sequence
from itertools import chain

from multiprocessing import Process, Queue
from queue import Empty as Empty

import networkx as nx
import ctypes

import random
from shmdict import shmdict, Struct

LIST_MP = 10000000
LIST_CH_MP = LIST_MP // 10000
LIST_IN_MP = 10


class DiGraph(nx.DiGraph):

    def next_pc(self, old_pc, channel):
        bb_name, index = old_pc
        bb_stmts = self.node[bb_name]['stmts']

        assert index < len(bb_stmts)

        next_index = (index + 1) % len(bb_stmts)

        if next_index:
            # Next vertex on the same basic block.
            return (bb_name, next_index)

        else:
            # Go to the next basic block according to the channel.
            try:
                _, next_bb, _ = next(filter(lambda x: channel in x[2]['chn'],
                                            self.out_edges((bb_name, ),
                                                           data=True)))

            except StopIteration as si:
                raise AssertionError(
                    'Cannot find appropriate basic block'
                ) from si

            return (next_bb, next_index)


class Worker:

    def __init__(self, wid, cfg, tasks, queues):

        self.wid = wid
        self.nonce = 0
        self.cfg = cfg
        self.queues = queues
        self.n_workers = len(queues)

        self.tasks = deque(tasks)
        self.tasks_suspended = deque(tasks)

    @property
    def is_ready(self):
        return bool(self.tasks)

    def event_loop(self):

        while True:
            try:
                is_blocked = not self.is_ready
                r = self.queues[self.wid].get(is_blocked)
            except Empty:
                break

            if r[0] == 'task':
                t = Task(*r[1:])
                self.tasks.append(t)

            # print('New req at worker %d: %s' % (self.wid, r))

        return True

    def send(self, wid, data):
        self.queues[wid].put(data)

    def run(self):

        self.sessions = shmdict('sessions', 100, {'idx': ctypes.c_int,
                                                  'ir': ctypes.c_int})

        self.msgs = shmdict('msgs', 100)

        self.reductors = shmdict('reductors', 100)

        while self.event_loop():

            task = self.tasks.popleft()
            bb_name, index = task.pc
            bb_stmts = self.cfg.node[bb_name]['stmts']
            func, inputs, outputs = bb_stmts[index]

            if len(inputs) == 1:
                # Execute vertex
                assert inputs[0] == task.channel

                # print(func.__closure__[0].cell_contents.__name__)

                if func.cat == 'transductor':

                    output = func(task.channel, task.content)

                    # For now expect transductors eager to have easier bracket
                    # handling.
                    assert len(outputs) == len(output)

                    for i, (channel, msg) in enumerate(zip(outputs, output)):

                        list_id = task.list_id + i * LIST_CH_MP

                        m = Message(msg, task.index, list_id)

                        next_pc = self.cfg.next_pc(task.pc, channel)
                        t = m.to_task(channel, next_pc)

                        self.tasks.append(t)

                elif func.cat == 'inductor':

                    output = func(task.channel, task.content)

                    seqs = tuple([output[i]] for i in range(len(outputs)))

                    while func.cont:
                        for i, m in enumerate(func(None, func.cont)):
                            seqs[i].append(m)

                    # --

                    task_seqs = tuple([] for i in range(len(outputs)))

                    for i, (channel, seq) in enumerate(zip(outputs, seqs)):

                        ts = task_seqs[i]

                        next_pc = self.cfg.next_pc(task.pc, channel)
                        list_id = task.list_id + i * LIST_CH_MP\
                            + task.index * LIST_IN_MP

                        for index, msg in enumerate(seq):
                            m = Message(msg, index, list_id)
                            t = m.to_task(channel, next_pc)
                            ts.append(t)

                        ts[-1].sm_inc(task.sm)

                    # TODO: proper task distribution. Critical part of
                    # performance, implement something more sophisticated.

                    tasks_parted = partition(chain(*task_seqs),
                                             self.n_workers)

                    self.tasks.extend(tasks_parted[self.wid])

                    for wid, tasks in enumerate(tasks_parted):
                        if wid != self.wid:
                            for t in tasks:
                                self.send(wid, t.dump())

                elif func.cat == 'reductor':
                    rkey = '%s_%d' % (bb_name, index)
                    skey = '%s_%d_%d' % (bb_name, index, task.list_id)
                    mkey = '%s_%d_%d_%d' % (bb_name, index, task.list_id, task.index)

                    # Register the reductor globally if needed.
                    #if rkey not in self.reductors and task.index == 0:
                    #    self.reductors[rkey] = 

                    if skey not in self.sessions:
                        if task.index == 0:
                            # Create new session
                            self.sessions[skey] = Struct(idx=task.index, ir=0)

                        else:
                            self.tasks_suspended.append(task)
                            # Register the message location
                            self.msgs[mkey] = self.wid
                            continue

                    session = self.sessions[skey]

                    func.cont = None if task.index == 0 else session.ir
                    func(task.channel, task.content)

                    if task.sm is not None:
                        list_id = task.list_id + i * LIST_CH_MP\
                            + task.index * LIST_IN_MP

                        m = Message(func.cont, task.index, list_id)
                        pass

            else:
                # Synchronisation point for inputs
                pass

            del task


class Message:

    def __init__(self, content, index, list_id, sm=None):
        self.content = content
        self.index = index
        self.sm = sm
        self.list_id = list_id

    def __repr__(self):
        supers = lambda n: ''.join(chr(8304 + int(i)) for i in str(n))
        ss = lambda n: ''.join(chr(8320 + int(i)) for i in str(n))
        return '<%d:M%s,%s%s>' % (self.list_id,
                                  ss(self.index), type(self.content).__name__,
                                  ',\u03C3%s' % ss(self.sm) if self.sm is not None else '')

    def to_task(self, channel, pc):
        return Task(self.content, self.index, self.list_id,
                    channel, pc, self.sm)

    def sm_inc(self, sm_init=-1):
        if sm_init != -1:
            self.sm = sm_init

        if self.sm == 0:
            pass

        else:
            self.sm = (self.sm or 0) + 1

    def sm_dec(self, sm_init=-1):
        if sm_init != -1:
            self.sm = sm_init

        if self.sm == 0 or self.sm == None:
            pass

        elif self.sm == 1:
            self.sm = None

        else:
            self.sm = self.sm - 1


class Task(Message):

    def __init__(self, content, index, list_id, channel, pc, sm=None):
        super().__init__(content, index, list_id, sm)
        self.channel = channel
        self.pc = pc

    def __repr__(self):
        return '<Task: %s, %s, %s>' % (super().__repr__(), self.channel,
                                       self.pc)

    def dump(self):
        return ('task', self.content, self.index, self.list_id, self.channel, self.pc,
                self.sm)

#------------------------------------------------------------------------------

def partition(lst, n):
    lst = list(lst)
    return [lst[i::n] for i in range(n)]


class Runner:

    def __init__(self, cfg, __input__, n_workers=2):

        self.list_id = 1
        self.tasks = []
        self.workers = []
        self.processes = None

        for channel, msgs in __input__.items():
            s = Stream(msgs, self.list_id)
            self.list_id = s.list_id

            init_pc = (cfg.entry[channel], 0)

            for msg in s.stream:
                t = msg.to_task(channel, init_pc)
                self.tasks.append(t)

            tasks_parted = partition(self.tasks, n_workers)

            queues = [Queue() for i in range(n_workers)]

            self.workers = [Worker(wid, cfg, tasks, queues)
                            for wid, tasks in enumerate(tasks_parted)]

    def run(self):

        self.processes = [Process(target=w.run) for w in self.workers]

        for p in self.processes:
            p.start()


#------------------------------------------------------------------------------

class Stream:

    def __init__(self, msgs, list_id=0):
        self.stream = []
        self.depth = None

        self.index = 0
        self.list_id = list_id

        self.bc = 0
        self.bmax = 0

        self._traverse(msgs)

    @property
    def new_list_id(self):
        return self.list_id * LIST_MP

    def _traverse(self, stream, level=1):

        inner = None
        assert isinstance(stream, Sequence)

        length = len(stream)

        for i, e in enumerate(stream, 1):

            if isinstance(e, Sequence):
                # Nested list

                if self.bc > 0:
                    self.bc -= 1

                    if self.bc == 0:
                        self.stream[-1].sm = self.bmax
                        self.index = 0
                        self.list_id += 1
                        self.bmax = 0

                if inner is True:
                    raise ValueError('Wrong sequence')

                inner = False
                self._traverse(e, level+1)

            else:
                # Message
                if inner is False:
                    raise ValueError('Wrong sequence')

                inner = True
                msg = Message(e, self.index, self.new_list_id)
                self.index += 1
                # level is unused
                self.stream.append(msg)

        self.bc += 1
        self.bmax +=1

        if level == 1:
            self.stream[-1].sm = 0
            self.depth = self.bc
            self.list_id += 1

    def __repr__(self):
        return repr(self.stream)
