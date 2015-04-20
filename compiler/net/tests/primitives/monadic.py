#!/usr/bin/env python3

'''
net Monadic (in | out1, out2)
connect
  <in|Reduce|out1, out2>
end
'''


import communication as comm


def c_Reduce(m1, m2):
    '2MU'
    a = m1['n']
    b = m2['n']
    c = a + b
    return ('partial', {1: [{'n': c}]}, {'n': c})


__input__ = {'in': [
    comm.Record({'n': 1}),
    comm.Record({'n': 2}),
    comm.Record({'n': 3}),
    comm.Record({'n': 4}),
    comm.SegmentationMark(3),
    comm.SegmentationMark(4),
    comm.Record({'n': 5}),
    comm.SegmentationMark(0),

]}

import astrakahn
astrakahn.start()
