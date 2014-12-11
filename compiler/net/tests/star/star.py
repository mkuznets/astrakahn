#!/usr/bin/env python3

'''
net Star (a| a, rewire, output)
synch star [NETIN=a, NETOUT=_a, BYPASS=a]
connect
  star .. <_a|Test|a>
end
'''


import communication as comm


def c_Test(m):
    '1T'
    n = m['n']
    mc = m.copy()
    if n <= 20:
        n += 1
        mc.update({'n': n})
        return ('send', {0: mc}, None)


__input__ = {'a': [
    comm.Record({'n': 0}),
    comm.Record({'n': 0}),
    comm.Record({'n': 0}),
    #comm.Record({'n': 0, '__ffp__': 1}),
    comm.Record({'n': 0, '__rfp__': 1}),
    comm.Record({'n': 0}),
    comm.Record({'n': 0}),
    #comm.Record({'n': 0}),
]}


import astrakahn
astrakahn.start()
