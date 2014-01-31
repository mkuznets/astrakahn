#!/usr/bin/env python3

from multiprocessing import Process, Queue, Event
from time import sleep
from copy import copy
from random import random
from types.py import Msg


class Channel:
    """
    AstraKahn channel
    TODO: strongly depends on the Queue implementation
    (that is currently taken from `multiprocessing' module)
    """

    def __init__(self, id_channel, name=None, depth=None, queue=None):
        self.queue = Queue() if not queue else queue
        self.ready = Event()
        self.ready.set()

        # Paramaters of the channel
        self.id = id_channel
        self.name = name if name != None else '_' + str(self.id)
        self.depth = depth
        self.critical_pressure = 10


    def get(self):
        """
        Get a message from the channel
        """

        if not self.is_critical():
            self.ready.set()

        return self.queue.get()

    def put(self, msg):
        """
        Put a message to the channel
        """

        self.ready.wait()

        if not self.is_critical():
            self.ready.set()
        else:
            self.ready.clear()

        return self.queue.put(msg)

    def pressure(self):
        """
        Return the pressure value of the channel.

        In the current model the pressure value is simply a number of messages
        in the channel.  The network supposed to work correctly under such
        assumption.  However, for the computations to be effective more
        sophisticated definition of pressure must be elaborated.
        """

        queue_size = self.queue.qsize()
        return queue_size if queue_size > 0 else 0

    def is_critical(self):
        return self.pressure() >= self.critical_pressure


class Message:
    """
    Superclass of all types of messages
    """

    def is_segmark(self):
        """
        The message is considered to be a data message by default rather than
        a segmentation mark.
        """
        return False


class SegmentationMark(Message):
    """
    Segmentation marks in the AstraKahn can be thought of as a combination of
    equal number of closing and opening brakets:

    .. math::
        \\underbrace{)...)}_{k} \\underbrace{(...(}_{k}

    where k is a parameter of the segmentation mark.
    """

    def __init__(self, n):
        # Number of opening and closing brakets.
        self.n = n
    def is_segmark(self):
        return True

class DataMessage(Message):
    """
    Regular data messages
    """

    def __init__(self, content):
        # TODO: not sure at the moment about the type of content.
        self.content = content


# Abstract AstraKahn vertex can be either a box or a syncroniser.
class Vertex:
    def __init__(self, inputs, outputs):

        # Number of channel names mustn't exceed the overall number of channels
        assert(inputs[0] >= len(inputs[1]) and outputs[0] >= len(outputs[1]))

        # Check for correspondence of indexes
        assert(len(inputs[1]) == 0 or (0 <= min(inputs[1].keys()) and max(inputs[1].keys()) < inputs[0]))
        assert(len(outputs[1]) == 0 or (0 <= min(outputs[1].keys()) and max(outputs[1].keys()) < outputs[0]))

        self.input_channels = {i: None for i in range(inputs[0])}
        self.output_channels = {i: None for i in range(inputs[0])}

    # Assign the queue to the input/output channels
    def set_input(self, id, queue):
        self.input_channels[id] = Channel(id_channel=id, queue=queue)

    def set_output(self, id, queue):
        self.output_channels[id] = Channel(id_channel=id, queue=queue)

    # Create unwired channels
    def init_free_channels(self):
        for (id, c) in self.input_channels.items():
            if c == None:
                self.input_channels[id] = Channel(id_channel=id)

        for (id, c) in self.output_channels.items():
            if c == None:
                self.output_channels[id] = Channel(id_channel=id)

    # Wire two vertex by the channels' ids
    def wire(self, output, vertex, input):
        c = Queue()
        self.set_output(output, c)
        vertex.set_input(input, c)


# Stateless box: transductor, inductor or reductor.
class Box(Vertex):
    def __init__(self, inputs, outputs, box_function):
        super(Box, self).__init__(inputs, outputs)
        self.function = box_function

    def start(self):
        # TODO: the implicit call - possibly poor desigh decision
        self.init_free_channels()

        self.thread = Process(target=self.protocol)
        self.thread.start()

    def stop(self):
        self.thread.terminate()

    def protocol(self):
        raise NotImplementedError("Protocol is not implemented.")

class Transductor(Box):
    def __init__(self, inputs, outputs, box_function):

        # Intuctor has a single input and one or more outputs
        assert(inputs[0] == 1 and inputs[0] >= 1)

        super(Transductor, self).__init__(inputs, outputs, box_function)

    def protocol(self):

        msg = None

        while True:
            msg = self.input_channels[0].get()
            assert(isinstance(msg, Message))

            if not msg.is_segmark():
                out_data = self.function.run(self.function.passport, msg.content)

                # Send the message out
                self.output_channels[0].put(DataMessage(out_data))

            else:
                # Segmentation marks are transferred as is through transductor
                self.outputs_channels[0].put(msg)


# Combination of a pure box function and its passport.
class BoxFunction:
    def __init__(self, function, passport):
        self.passport = passport
        self.run = function

###############################################################################

passport_f = ({'sum': int, 'mul': float}, {'sum': int, 'mul': float})
passport_test = ([int, int, object], {'sum': int, 'mul': float})

def f(passport, input):
    input_values = copy(input)

    print(input)

    (sum, mul) = passport[0].keys()
    mul_field = passport['in'][1]

    input_values[sum_field] += input_values[sum_field]
    input_values[mul_field] *= 3

    sleep(1)

    return input_values

def get_output(channel):
    while True:
        channel.get()
        print("Get, pressure = " + str(channel.pressure()))
        sleep(5 * random())

if __name__ == "__main__":

    try: # Create transductors
        a = Transductor(inputs=(1, {0: 'a'}), outputs=(1, {0: 'a'}), box_function=BoxFunction(f, passport_test))
        b = Transductor(inputs=(1, {0: 'a'}), outputs=(1, {0: 'a'}), box_function=BoxFunction(f, passport_f))

        a.wire(0, b, 0)
        #b.wire(0, a, 0)

        a.start()
        #b.start()

        getout = Process(target=get_output,  args=(a.output_channels[0],))
        getout.start()

        for i in range(1000):
            a.input_channels[0].put(DataMessage({'sum': i, 'mul': i}))
            print("Msg: " + str(i) + ", pressure = " + str(a.input_channels[0].pressure()))
            sleep(0.5)

        a.thread.join()
        b.thread.join()

    except KeyboardInterrupt:
        a.stop()
        b.stop()
