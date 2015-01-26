#!/usr/bin/env python3

'''
net Factorial (_1 | _1)
connect
  gen# .. a .. b
end
'''


import communication as comm


def c_a(m):
    '1T'
    n = m['n']
    print(n)
    return ('send', {0: {'n': 1}}, None)


def c_b(m):
    '1T'
    import time
    n = m['n']
    time.sleep(1)
    return ('send', {0: {'n': 1}}, None)


def c_gen(m):
    '1I'
    n = m['n']
    if n == 1:
        return ('terminate', {}, None)
    else:
        sn = n
        n -= 1
        return ('continue', {0: {'n': sn}}, {'n': n})

__input__ = {'_1': []}

from random import randint

__input__['_1'].append(comm.Record({'n': 6}))
__input__['_1'].append(comm.Record({'n': 5}))
__input__['_1'].append(comm.Record({'n': 3}))
__input__['_1'].append(comm.SegmentationMark(3))
__input__['_1'].append(comm.Record({'n': 4}))
__input__['_1'].append(comm.SegmentationMark(3))
__input__['_1'].append(comm.Record({'n': 2}))
__input__['_1'].append(comm.SegmentationMark(0))

#__input__['in'].append(comm.SegmentationMark(0))

import astrakahn
astrakahn.start()
