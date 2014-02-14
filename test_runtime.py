#!/usr/bin/env python3

import components
import os
import helpers
from copy import copy
from time import sleep

passport_f = ({'sum': int, 'mul': float}, {'sum': int, 'mul': float})


def f(input):
    input_values = copy(input)

    input_values['sum'] += input_values['sum']
    input_values['mul'] *= 3

    sleep(1)

    return input_values


try:  # Create transductors
    box_f = components.BoxFunction(f, passport_f)

    a = components.Transductor(inputs=(1, {0: 'a'}), outputs=(1, {0: 'a'}),
                               box_function=box_f, parameters={'pid': os.getpid()})
    b = components.Transductor(inputs=(1, {0: 'a'}), outputs=(1, {0: 'a'}),
                               box_function=box_f, parameters={'pid': os.getpid()})

    a.wire(0, b, 0)
    #b.wire(0, a, 0)

    a.start()
    #b.start()

    helpers.emit_agent('producer', a.input_channels[0])
    helpers.emit_agent('consumer', a.output_channels[0])

    a.thread.join()
    print("that's it")
    #b.thread.join()

except KeyboardInterrupt:
    a.stop()
    #b.stop()
