from aksync.runtime import *
from aksync.compiler import compile
from collections import deque

sync_src = """
synch cpu (instr, load, mem, c | stdout, load, mem, c)
{
  store mem;
  state int(2) found;

  # LD  0
  # ST  1
  # ADD 2
  # MUL 3
  # PRT 4

  state int(5) opcode;
  state int(10) operand;
  state int(10) acc = 0;

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
      c.(act) & [opcode == 0] {
        set found = [0];
        send @[0] => mem;
        goto search;
      }

      # Store
      c.(act) & [opcode == 1] {
        send (addr: operand || value: [acc]) => mem;
        goto start;
      }

      # Addition
      c.(act) & [opcode == 2] {
        set acc = [acc + operand];
        goto start;
      }

      # Multiplication
      c.(act) & [opcode == 3] {
        set acc = [acc * operand];
        goto start;
      }

      # Print
      c.(act) & [opcode == 4] {
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
"""

sync_py = compile(sync_src)
exec(sync_py)

# Expect cpu() and cpu_init() to be defined here.

LD, ST, ADD, MUL, PRT = range(0, 5)

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

istream.reverse()

channels = {
    0: deque(({'opc': opc, 'op0': op} for opc, op in istream)),  # instr
    1: deque(),  # load
    2: deque(),  # mem
    3: deque(),  # c
}

state = cpu_init()

# Implement network
# Input: `instr'
# Output: `stdout'
# `load', `mem', and `c' are connected via feedback loop.

while True:
    inputs = {i: ch[-1] for i, ch in channels.items() if ch}

    output, state, consumed = cpu(inputs, state)

    if not consumed:
        break

    for i in consumed:
        channels[i].pop()

    for i, msgs in output.items():
        if i > 0:
            channels[i].extendleft(msgs)

    if 0 in output:
        print('Out', output[0])
