#!/usr/bin/env python3

import components
import os
import helpers
from copy import copy
from time import sleep

passport_f = ({'sum': int, 'mul': float}, {'sum': int, 'mul': float})
passport_f_ind = ({'n': int, 'num': float, 'i': int}, {'n': int, 'num': float, 'i': int})


def f(input):
    input_values = copy(input)

    input_values['sum'] += input_values['sum']
    input_values['mul'] *= 3

    sleep(1)

    return {0: input_values}


def f_ind(input):
    input_values = copy(input)
    result = {}

    input_values['num'] = 5 * input_values['num'] + 10
    input_values['i'] += 1

    #sleep(1)

    result[0] = input_values
    if input_values['i'] < 5:
        result['continuation'] = input_values

    return result

try:  # Create transductors
    box_f = components.BoxFunction(f, passport_f)
    box_f_ind = components.BoxFunction(f_ind, passport_f_ind)

    a = components.Transductor(inputs=(1, {0: 'a'}), outputs=(1, {0: 'a'}),
                               box_function=box_f)
    b = components.Transductor(inputs=(1, {0: 'a'}), outputs=(1, {0: 'a'}),
                               box_function=box_f)

    c = components.Inductor(inputs=(1, {0: 'a'}), outputs=(1, {0: 'a'}),
                            box_function=box_f_ind)

    #a.wire(0, b, 0)

    c.start()

    helpers.emit_agent('producer', c.input_channels[0])
    helpers.emit_agent('consumer', c.output_channels[0])

    c.thread.join()
    print("that's it")
    #b.thread.join()

except KeyboardInterrupt:
    c.stop()
    #b.stop()
