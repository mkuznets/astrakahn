#!/usr/bin/env python3

'''
net CPU (instr | stdout)
  synch cpu [SIZE=32]
connect
  cpu\\
end
'''

#------------------------------------------------------------------------------

s_cpu = '''
@SIZE = 10
synch cpu (instr, load, mem, c | stdout, load, mem, c)
{
  store mem;
  state int(2) found;

  state int(SIZE) acc;

  state enum(NONE, LD, ST, ADD, MUL, PRT) opcode;
  state int(SIZE) operand;

  # Initial state: wait for instructions.
  start {

    # Set found mem-value to acc.
    on:
      load.(value) {
        set acc = [value];
      }

    # Instruction stream.
    elseon:
      instr.(opc, op0) {
        set opcode = [opc], operand = [op0];
        send (act: [1]) => c;
        goto idecode;
      }
  }

  # Decode instruction opcode.
  idecode {
    on:
      # Load
      c.(act) & [opcode == LD] {
        set found = [0];
        send @[0] => mem;
        goto search;
      }

      # Store
      c.(act) & [opcode == ST] {
        send (addr: operand || value: [acc]) => mem;
        goto start;
      }

      # Addition
      c.(act) & [opcode == ADD] {
        set acc = [acc + operand];
        goto start;
      }

      # Multiplication
      c.(act) & [opcode == MUL] {
        set acc = [acc * operand];
        goto start;
      }

      # Print
      c.(act) & [opcode == PRT] {
        send 'acc => stdout;
        goto start;
      }

      # Error: couldn't decode instruction.
      c.else {
        send (error: [1]) => stdout;
        goto start;
      }
  }

  search {
    on:
      # Skip.
      mem.(addr, value) & [addr != operand] {
        send this => mem;
      }

      # Match.
      mem.(addr || tail) & [addr == operand] {
        set mem = this,
            found = [1];
        send tail => mem;
      }

      # End of list: success
      mem.@d & [d == 0 && found == 1] {
        send mem => load;
        goto start;
      }

      # End of list: not found
      mem.@d & [d == 0 && found == 0] {
        send (error: [1]) => stdout;
        goto start;
      }
  }
}
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

#------------------------------------------------------------------------------

import astrakahn
astrakahn.start()
