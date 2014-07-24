#!/usr/bin/env python3
import network as net
import inspect


def box(cat, inputs, outputs):
    def wrap(f):
        f.spec = net.box_spec(cat)
        f.inputs = inputs
        f.outputs = outputs
        return f
    return wrap

class Sort(net.Net):
    @box('1T' , ['in'], ['out'])
    def foo(a):
        return a + 1

n = Sort()

print(inspect.getmembers(n, predicate=inspect.ismethod))
