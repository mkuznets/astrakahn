#!/usr/bin/env python3

'''
net Factorial (in | out)
connect
  <in|Test|init,n> .. <n|Gen|terms,init> .. <init,terms|Reduce|out>
end
'''


import communication as comm


def c_Test(m):
    '2T'
    n = m['n']
    if n <= 1:
        return ('send', {0: {'n': 1}, 1: {'n': 1}}, None)
    else:
        return ('send', {0: {'n': 1}, 1: {'n': n}}, None)


def c_Gen(m):
    '2I'
    n = m['n']
    if n == 1:
        return ('terminate', {}, None)
    else:
        sn = n
        n -= 1
        return ('continue', {0: {'n': sn}}, {'n': n})


def c_Reduce(m1, m2):
    '1DU'
    a = m1['n']
    b = m2['n']
    c = a * b
    return ('partial', {}, {'n': c})


__input__ = {'in': []}


from random import randint

for i in range(100):
    __input__['in'].append(comm.Record({'n': randint(2, 100)}))
    __input__['in'].append(comm.SegmentationMark(0))

import astrakahn
astrakahn.start()
