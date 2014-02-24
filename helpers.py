#!/usr/bin/env python3

from multiprocessing import Process
import communication as comm
from time import sleep
from random import random
import sys


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
        msg = channel.get()
        print("Get, pressure = "
              + str(channel.pressure())
              + " --- "
              + str(msg.content))
        #sleep(5 * random())


def main_producer_function(channel):
    for i in range(1000):
        channel.ready.wait()

        channel.put(comm.DataMessage({'n': i, 'num': float(i), 'i': 0}))
        print("Msg: " + str(i)
              + ", pressure = " + str(channel.pressure()))
        sleep(0.5)
