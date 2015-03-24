#!/usr/bin/env python3

'''
net Factorial (in, _in | out, _out)
morph { Induce / Map / Reduce }
synch Guard
synch Router
connect
  Guard|out=_1> .. Induce .. <_1,_in|~|_1> .. Map .. <_1|Router|out=_1> .. Reduce|out>
end
'''


import communication as comm


s_Guard = '''
synch Guard (in, __nfrag__, __refrag__ | out)
{
  state int(32) nfrag = 10, ntmp=10,
                refrag = 0, refragtmp = 0;

  start {
    on:
      in.@d {
        set nfrag = [ntmp], refrag = [refragtmp];
        send this => out;
      }

    elseon:
      in & [refrag] {
        send (__nfrag__: nfrag || 'refrag || this) => out;
      }

      in.else {
        send (__nfrag__: nfrag || this) => out;
      }

      __nfrag__.(n) {
        set ntmp = [n];
      }

      __refrag__.(r) {
        set refragtmp = [r];
      }
  }
}
'''


s_Router = '''
synch Router (in | out, _out)
{
  state int(1) last = 0;

  start {
    on:
      in.@d & [last == 0] {
        send this => out;
      }

      in.@d & [last == 1] {
        send this => _out;
      }

    elseon:
      in.(refrag) & [refrag == 0] {
        set last = [0];
        send this => out;
      }

      in.(refrag) & [refrag == 1] {
        set last = [1];
        send this => _out;
      }

    elseon:
      in {
        # Default destination: to refragmentation.
        set last = [0];
        send this => out;
      }
  }
}
'''

def c_Map(msg):
    '1T*'
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

__input__['in'].append(comm.Record({'lst': [random.random() for i in
                                            range(100)], '__nfrag__': 7}))
__input__['in'].append(comm.SegmentationMark(0))
__input__['_in'].append(comm.SegmentationMark(0))

import astrakahn
astrakahn.start()
