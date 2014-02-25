#!/usr/bin/env python3

# SLOPPY HACK
import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

import components
import communication as comm
import helpers
from copy import copy
import math
from multiprocessing import Queue

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
    msg = 0
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

    # Number of input messages
    limit = 100

    # The output is passed through this queue
    main_out = Queue()

    producer = helpers.emit_agent(agent_type='producer',
                                  channel=a.input_channels[0],
                                  msg_generator=generator,
                                  limit=100, delay=0)
    consumer = helpers.emit_agent(agent_type='consumer',
                                  channel=b.output_channels[0],
                                  limit=100, delay=0, data=main_out)

    # Receive the output from the network.
    ref_result = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53,
                  59, 61, 67, 71, 73, 79, 83, 89, 97]


    result = []
    while True:
        msg = main_out.get()
        if msg.end_of_stream():
            break
        result += [msg.content['prime']]

    print("\n\n=================")
    if result == ref_result:
        print("Test passed")
    else:
        print("Test failed")



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
