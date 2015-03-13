#!/usr/bin/env python3

'''
net synchtab (in1, in2 | out1, out2)
  tab [inc] synch foo
connect
  foo
end
'''

#------------------------------------------------------------------------------

s_foo = '''
@inc = 45
synch foo (in1, in2 | out1, out2)
{
  start {
    on:
      in1.(n || tail) {
        send (tail || n: [n+inc]) => out2;
      }
  }
}
'''

#------------------------------------------------------------------------------

import communication as comm

__input__ = {'in1':
             [comm.Record({'n': 0, 'a': 100})]
             }

#------------------------------------------------------------------------------

import astrakahn
astrakahn.start()
