#!/usr/bin/env python3

'''
net Factorial (m | m)
connect
  <m|a|m,m>
end
'''


import communication as comm


def c_a(m):
    '2T*'
    n = m['n']

    for i in range(250 * (20 - n)):
        z = sum(1.1**j for j in range(i))
    return ('send', {0: [{'n': n, 'z': z}], 1: [{}]}, None)


def c_b(m):
    '2T'
    import time
    n = m['n']
    time.sleep(1)
    return ('send', {0: [{'n': 1}]}, None)


def c_gen(m):
    '1I'
    n = m['n']
    if n == 1:
        return ('terminate', {}, None)
    else:
        sn = n
        n -= 1
        return ('continue', {0: [{'n': sn}]}, {'n': n})

__input__ = {'m': []}

from random import randint

for i in range(20):
    __input__['m'].append(comm.Record({'n': i}))

__input__['m'].append(comm.SegmentationMark(0))

#__input__['m'].append(comm.SegmentationMark(3))
#__input__['m'].append(comm.Record({'n': 4}))
#__input__['m'].append(comm.SegmentationMark(3))
#__input__['m'].append(comm.Record({'n': 2}))
#__input__['m'].append(comm.SegmentationMark(0))

import astrakahn
astrakahn.start()
