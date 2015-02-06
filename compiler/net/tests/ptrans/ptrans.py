#!/usr/bin/env python3

'''
net PTrans (in|out)
synch __R__
synch __M__
synch __D__

connect
  (__R__ .. <r|~|t1, t2, t3, t4> .. (

    <t1|Test|__mrg__>
    || <t2|Test|__mrg__>
    || <t3|Test|__mrg__>
    || <t4|Test|__mrg__>

  ) .. __M__)\\
end
'''


s___R__ = '''
synch __R__ (in, __fb__ | r, __sm__)
{
  state int(32) seg_len;

  start {
    on:
      in.@depth {
        send (d: depth || l: seg_len) => __sm__;
        goto wait_feedback;
      }

      in.else {
        set seg_len = [seg_len + 1];
        send this => r;
      }
  }

  wait_feedback {
    on:
      __fb__ {
        set seg_len = [0];
        goto start;
      }
  }
}
'''

s___D__ = '''
synch __D__ (__rtr__ | __t1__, __t2__, __t3__, __t4__)
{
  start {
    on:
      __rtr__ {
        send (this || t1: [1]) => __t1__;
      }

      __rtr__ {
        send (this || t2: [1]) => __t2__;
      }

      __rtr__ {
        send (this || t3: [1]) => __t3__;
      }

      __rtr__ {
        send (this || t4: [1]) => __t4__;
      }
  }
}
'''

s___M__ = '''
synch __M__ (__mrg__, __sm__ | out, __fb__)
{
  state int(32) seg_len, exp_len, depth;

  start {
    on:
      __mrg__ & [seg_len == (exp_len - 1)] {
        set seg_len = [0], exp_len = [-1];
        send this => out,
             @depth => out,
             (confirm : [1]) => __fb__;
      }

      __mrg__.else {
        set seg_len = [seg_len + 1];
        send this => out;
      }

      __sm__.(d, l) & [seg_len == l] {
        set seg_len = [0], exp_len = [-1];
        send @d => out,
             (confirm : [1]) => __fb__;
      }

      __sm__.(d, l) & [seg_len < l]  {
        set exp_len = [l], depth = [d];
      }
  }
}
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
    return ('send', {0: [mc]}, None)


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
