#!/usr/bin/env python3

import akr

from aksync.runtime import *
from random import choice
from collections import defaultdict, ChainMap

@akr.reductor(False)
def summ(m):
    if summ.cont is None:
        summ.cont = 0
    summ.cont = m + summ.cont

@akr.inductor
def gen(m):
    r = m+1
    gen.cont = r if r < 10 else None
    return (r, )

@akr.transductor
def bar(m):
    r = m ** 2
    return (r, )

@akr.transductor
def foo(m):
    r1 = m - 1
    r2 = m + 1
    return (r1, r2)

@akr.output
def __output__(channel, msg):
    print(channel, msg)

class zip:
    @staticmethod
    def test(state, msgs, return_locals=False):
        if not msgs: return None

        valid_acts = []

        if state.name == "start":
            if msgs.get(1, None):
                if set() <= msgs[1].keys():
                    local_vars = zip._extract(msgs[1], 1)
                    if eval("True", state.scope(), local_vars):
                        valid_acts.append((1, 1, local_vars))
            if msgs.get(0, None):
                if set() <= msgs[0].keys():
                    local_vars = zip._extract(msgs[0], 0)
                    if eval("True", state.scope(), local_vars):
                        valid_acts.append((0, 0, local_vars))

        elif state.name == "s1":
            if msgs.get(1, None):
                if set() <= msgs[1].keys():
                    local_vars = zip._extract(msgs[1], 2)
                    if eval("True", state.scope(), local_vars):
                        valid_acts.append((2, 1, local_vars))

        elif state.name == "s2":
            if msgs.get(0, None):
                if set() <= msgs[0].keys():
                    local_vars = zip._extract(msgs[0], 3)
                    if eval("True", state.scope(), local_vars):
                        valid_acts.append((3, 0, local_vars))

        if not valid_acts:
            return None

        act_id, port_id, local_vars = choice(valid_acts)

        if return_locals: return act_id, port_id, local_vars
        else: return act_id, port_id


    @staticmethod
    def execute(orig_state, msg, act_id, local_vars=None):
        state = orig_state.copy()
        output = defaultdict(list)
        if not local_vars: local_vars = zip._extract(msg, act_id)
        system = {"ChainMap": ChainMap, "__this__": msg}
        scope = dict(ChainMap(state.scope(), system))

        if act_id == 0:
            local_vars["ma"] = eval('__this__', scope, local_vars)
            state.name = "s1"
            state.update(local_vars)

        elif act_id == 1:
            local_vars["mb"] = eval('__this__', scope, local_vars)
            state.name = "s2"
            state.update(local_vars)

        elif act_id == 2:
            output[0].append(
               eval('dict(ChainMap(__this__, ma))', scope, local_vars)
            )
            state.name = "start"
            state.update(local_vars)

        elif act_id == 3:
            output[0].append(
               eval('dict(ChainMap(__this__, mb))', scope, local_vars)
            )
            state.name = "start"
            state.update(local_vars)


        return output, state

    @staticmethod
    def init():
        return State(name="start", ma={}, mb={})

    @staticmethod
    def _extract(msg, act_id):
        args = {
            0: ([], None, None),
            1: ([], None, None),
            2: ([], None, None),
            3: ([], None, None),
        }
        t = args[act_id]
        return extract(msg, *t)

    @staticmethod
    def run(state, msgs):
        test = zip.test(state, msgs, True)
        if test:
            act_id, port_id, local_vars = test
            output, state = zip.execute(state, msgs[port_id], act_id, local_vars)
            return(output, state, (port_id,))
        else: return {}, state, None

nodes = [
    ('bb_1', {'stmts': [(gen, ('_1',), ('_1',)), (foo, ('_1',), ('a', 'b')), (zip, ('a', 'b'), ('a',)), (bar, ('a',), ('_1',)), (summ, ('_1',), ('r1',))]}),
    ('bb_1_exit_r1', {'stmts': [(__output__, ('r1',), ())]}),
]

edges = [
    ('bb_1', 'bb_1_exit_r1', {'chn': {'r1'}}),
]

cfg = akr.DiGraph()
cfg.add_nodes_from(nodes)
cfg.add_edges_from(edges)
cfg.entry = {'_1': 'bb_1'}
cfg.exit = {'r1': 'bb_1'}

__input__ = {'_1': [[1, 2, 3], [4, 5, 6]]}

runner = akr.Runner(cfg, __input__)
runner.run()
