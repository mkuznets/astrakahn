#!/usr/bin/env python3

# SLOPPY HACK
import sys, os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

import components
import communication as comm
import os
import helpers
from copy import copy
from time import sleep
import math

###############################################

sieve_passport = {
    'input':  (int,),
    'output': (int,)
}

transform_passport = {
    'input':  (int,),
    'output': ({'n': int, 'prime': int},)
}

def sieve(input):
    """
    Sieve of Eratosthenes
    """

    n = copy(input)

    if n < 2:
        return None
    if n == 2:
        return {0: n}
    if not (n % 2):
        return None

    bound = math.sqrt(n)
    for i in range(3, int(bound)+1, 2):
        if not (n % i):
            return None
    return {0: n}


def transform(input):
    """
    Transform to a record
    """

    n = copy(input)

    return {0: {'prime': n}}

###############################################

def generator():
    msg = 8000
    while True:
        yield comm.DataMessage(msg)
        msg += 1

###############################################

try:
    sieve_internals = components.BoxFunction(sieve, sieve_passport)
    transform_internals = components.BoxFunction(transform, transform_passport)

    # Create transductors
    a = components.Transductor(inputs=(1, {0: 'a'}), outputs=(1, {0: 'a'}),
                               box_function=sieve_internals)

    b = components.Transductor(inputs=(1, {0: 'a'}), outputs=(1, {0: 'a'}),
                               box_function=transform_internals)

    a.wire(0, b, 0)

    a.start()
    b.start()

    producer = helpers.emit_agent(agent_type='producer',
                                  channel=a.input_channels[0],
                                  msg_generator=generator,
                                  delay=0)
    consumer = helpers.emit_agent(agent_type='consumer',
                                  channel=b.output_channels[0],
                                  delay=0)

    a.thread.join()
    a.thread.join()
    producer.join()
    consumer.join()

    print("Network has stopped.")

except KeyboardInterrupt:
    a.stop()
    b.stop()
    producer.terminate()
    consumer.terminate()
    print("Network has been stopped by user.")
