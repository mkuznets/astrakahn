#!/usr/bin/env python3

'''
net Factorial (_1, __1 | _1)
morph { Induce / Map / Reduce }
synch Guard
connect
  EqualSplit .. <_1, nfrag|Guard|_1> .. <_1,__1|~|_1> .. Induce .. Map .. Reduce
  #<in|Test|init,n> .. <n|Gen|terms,init> .. <init,terms|Reduce|out>
end
'''


import communication as comm


s_Guard = '''
synch Guard (in, __nfrag__ | out)
{
  state int(32) nfrag = 10, ntmp=10;

  start {
    on:
      in.@d {
        set nfrag = [ntmp];
        send this => out;
      }

      in.else {
        send (nfrag: [nfrag] || this) => out;
      }

      __nfrag__.(n) {
        set ntmp = [n];
      }
  }
}
'''

def c_EqualSplit(msg):
    '1T'
    n, m = len(msg['lst']), msg['m']

    size, rem = divmod(n, m)
    chunks = list(map(sum, zip([size] * m,
                                [1] * rem + [0] * (m - rem))))
    msg['chunks'] = chunks

    return ('send', {0: [msg]}, None)


def c_Map(msg):
    '1T'
    msg['sum'] = sum(msg['lst'])
    del msg['lst']
    return ('send', {0: [msg]}, None)


def c_Induce(msg):
    '1I'
    if not msg['lst']:
        return ('terminate', {}, None)
    else:
        chunks = msg['chunks']
        out_msg = msg.copy()
        n = msg['chunks'].pop()

        out_msg['lst'] = msg['lst'][:n]
        msg['lst'] = msg['lst'][n:]
        del out_msg['chunks']

        return ('continue', {0: [out_msg]}, msg)


def c_Reduce(m1, m2):
    '1MU'
    m1['sum'] += m2['sum']
    return ('partial', {}, m1)


__input__ = {'_1': [], '__1': []}

import random

__input__['_1'].append(comm.Record({'lst': [random.random() for i in
                                            range(10)], 'm': 10}))
__input__['_1'].append(comm.SegmentationMark(0))
__input__['__1'].append(comm.SegmentationMark(0))

import astrakahn
astrakahn.start()
