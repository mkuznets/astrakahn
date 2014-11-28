#!/usr/bin/env python3

'''
net Factorial (in | out)
connect
  <in|Test|init,n> .. <n|Gen|terms,init> .. <init,terms|Reduce|out>
end
'''

def c_Test(n):
    '2T'
    if n <= 1:
        return ('send', {0: 1, 1: 1}, None)
    else:
        return ('send', {0: 1, 1: n}, None)


def c_Gen(n):
    '2I'
    if n == 1:
        return ('terminate', {}, None)
    else:
        sn = n
        n -= 1
        return ('continue', {0: sn}, n)


def c_Reduce(a, b):
    '1DU'
    c = a * b
    return ('partial', {}, c)

__input__ = {'in': [1, 2, 3]}

import astrakahn
astrakahn.start()
