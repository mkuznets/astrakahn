#!/usr/bin/env python3

'''
net PTrans (in|out)
synch __R__ "r.sync"
synch __M__ "m.sync"
synch __D__ "d.sync"

connect
  <in|~|__in__> .. (__R__ .. __D__ .. (

    <__t1__|Test|__mrg__>
    || <__t2__|Test|__mrg__>
    || <__t3__|Test|__mrg__>
    || <__t4__|Test|__mrg__>

  ) .. __M__)\ .. <__out__|~|out>
end
'''


import communication as comm


def c_Test(m):
    '1T'
    import time, os

    n = m['n']
    mc = m.copy()

    n += 0
    mc.update({'n': n})

    #time.sleep(10)
    return ('send', {0: mc}, None)


__input__ = {'in': [
    comm.Record({'n': 1}),
    comm.Record({'n': 2}),
    comm.SegmentationMark(1),
    comm.Record({'n': 3}),
    comm.SegmentationMark(4),
    comm.Record({'n': 4}),
    comm.SegmentationMark(2),
    comm.Record({'n': 5}),
]}


import astrakahn
astrakahn.start()
