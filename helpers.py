#!/usr/bin/env python3

from multiprocessing import Process
import communication as comm
from time import sleep
from random import random

def emit_agent(agent_type, channel):

    if agent_type == 'producer':
        f = main_producer_function
    elif agent_type == 'consumer':
        f = main_consumer_function
    else:
        assert(False)

    agent_process = Process(target=f, args=(channel,))
    agent_process.start()

def main_consumer_function(channel):
    while True:
        channel.get()
        print("Get, pressure = " + str(channel.pressure()))
        sleep(5 * random())


def main_producer_function(channel):
    for i in range(1000):
        channel.put(comm.DataMessage({'sum': i, 'mul': float(i)}))
        print("Msg: " + str(i)
              + ", pressure = " + str(channel.pressure()))
        sleep(0.5)
