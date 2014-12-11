#!/usr/bin/env python3

'''
net CPU (instr | stdout)
  synch cpu [SIZE=32]
connect
  cpu\\
end
'''

#------------------------------------------------------------------------------

LD, ST, ADD, MUL, PRT = range(1, 6)

istream = [
    (PRT, 0),
    (ADD, 10),
    (PRT, 0),
    (MUL, 5),
    (PRT, 0),
    (ST, 1),
    (ADD, 100),
    (ST, 2),
    (PRT, 0),
    (LD, 1),
    (PRT, 0),
]

import communication as comm

__input__ = {'instr':
             [comm.Record({'opc': opc, 'op0': op}) for opc, op in istream]
             }

def __output__(stream):
    '''
    1H
    '''
    for entry in stream:
        pid, pname, msg = entry
        print('RR: %s: %s' % (pname, msg))

#------------------------------------------------------------------------------

import astrakahn
astrakahn.start()
