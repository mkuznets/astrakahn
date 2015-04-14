#!/usr/bin/env python3

'''
net Factorial (in, _in | out, _out, o1, o2)
morph { Induce / Map / Reduce }
connect
  # Manual morphism.
  #Marker|out=_1> .. Induce .. <_1,_in|~|_1> .. Map .. <_1|Router|out=_1> .. Reduce|out>

  # Proper morphism.
  <in, _in|Map|out, o1, o2>
end
'''


def c_Map(msg):
    '3T'
    msg['sum'] = sum(msg['lst'])
    del msg['lst']
    return ('send', {0: [msg]}, None)


def c_Induce(msg):
    '1I'
    if not msg['lst']:
        return ('terminate', {}, None)
    else:
        if 'chunks' not in msg:
            # Append a list of chunk sizes.
            n, nfrag = len(msg['lst']), msg['__nfrag__']

            size, rem = divmod(n, nfrag)
            msg['chunks'] = list(map(sum, zip([size] * nfrag,
                                              [1] * rem + [0] * (nfrag - rem))))
            print(msg['chunks'])

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


__input__ = {'in': [], '_in': []}

import random
import communication as comm

__input__['in'].append(comm.Record({'lst': [random.random() for i in
                                            range(100)], '__nfrag__': 7 }))
__input__['in'].append(comm.SegmentationMark(0))
__input__['_in'].append(comm.SegmentationMark(0))

import astrakahn
astrakahn.start()
