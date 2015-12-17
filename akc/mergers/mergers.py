#!/usr/bin/env python3

'''
net Mergers (a, b | c)
  synch merge_mix
  synch merge_switch
connect
  <a,b|merge_switch|c>
end
'''

#------------------------------------------------------------------------------
# Mergers


s_merge_switch = '''
synch merge_switch (a:k, b:k | c:k)
{
  start {
    on:
      a.() {
        send this => c;
        goto s_a;
      }

      b.() {
        send this => c;
        goto s_b;
      }

      a.@_ { }
      b.@_ { }
  }

  s_a {
    on:
      a.() {
        send this => c;
      }

      a.@_ {
        send this => c;
        goto start;
      }
  }

  s_b {
    on:
      b.() {
        send this => c;
      }

      b.@_ {
        send this => c;
        goto start;
      }
  }
}
'''


s_merge_mix = '''
synch merge_mix (a:k, b:k | c:k)
{
  state int(10) scnt = 0;
  start {
    on:
      a.() {
        send this => c;
      }

      b.() {
        send this => c;
      }

    elseon:
      a.@_ & [scnt < 1] {
        set scnt = [scnt + 1];
      }

      b.@_ & [scnt < 1] {
        set scnt = [scnt + 1];
      }

    elseon:
      a.@_ & [scnt == 1] {
        set scnt = [0];
        send this => c;
      }

      b.@_ & [scnt == 1]{
        set scnt = [0];
        send this => c;
      }
  }
}
'''


#------------------------------------------------------------------------------

if __name__ == '__main__':

    import astrakahn
    import communication as comm

    __input__ = {
        'a': [
            comm.Record({'A': 1}),
            comm.Record({'A': 2}),
            comm.Record({'A': 3}),
            comm.SegmentationMark(1),
            comm.Record({'C': 1}),
            comm.Record({'C': 2}),
            comm.Record({'C': 3}),
            comm.SegmentationMark(0),
        ],

        'b': [
            comm.Record({'B': 1}),
            comm.Record({'B': 2}),
            comm.SegmentationMark(1),
            comm.Record({'B': 3}),
            comm.Record({'B': 4}),
            comm.SegmentationMark(0),
        ],
    }

    def __output__(stream):
        '1H'

        import time

        for i, ch, msg in stream:

            content = msg.content

            print(time.time(), 'O: %s: %s' % (ch, content))

    astrakahn.start()
