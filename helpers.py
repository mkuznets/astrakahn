#!/usr/bin/env python3

from multiprocessing import Process
import communication as comm
from time import sleep
from random import random
import sys
import os
import itertools


def emit_agent(agent_type, channel, msg_generator=None, limit=None, delay=0):

    counter = itertools.count() if not limit else range(limit)

    if not (isinstance(delay, int) or isinstance(delay, float)) or delay < 0:
        delay = 0

    agent_process = Process(target=agent, args=(agent_type, channel,
                                                msg_generator, counter,
                                                delay,))
    agent_process.start()

    return agent_process


def agent(agent_type, channel, msg_generator, counter, delay):

    print(agent_type, os.getpid())

    if agent_type == 'producer':
        assert(msg_generator != None)
        gen_instance = msg_generator()

        for i in counter:
            channel.ready.wait()
            message = next(gen_instance)
            channel.put(message)

            print(message, "P =", channel.pressure())

            # Configurable delay
            sleep(delay)

    elif agent_type == 'consumer':
        for i in counter:
            message = channel.get()

            print("\t\t\t\t\t", message, "P =", channel.pressure())

            # Configurable delay
            sleep(delay)

    else:
        assert(False)
