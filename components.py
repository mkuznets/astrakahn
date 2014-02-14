#!/usr/bin/env python3

import communication as comm
from multiprocessing import Process, Queue
import typesystem as types
import os
import signal


# Abstract AstraKahn vertex can be either a box or a syncroniser.
class Vertex:
    def __init__(self, inputs, outputs, parameters=None):

        # Number of channel names mustn't exceed the overall number of channels
        assert(inputs[0] >= len(inputs[1]) and outputs[0] >= len(outputs[1]))

        # Check for correspondence of indexes
        assert(len(inputs[1]) == 0 or (0 <= min(inputs[1].keys())
                                       and max(inputs[1].keys()) < inputs[0]))
        assert(len(outputs[1]) == 0
               or (0 <= min(outputs[1].keys())
                   and max(outputs[1].keys()) < outputs[0]))

        self.input_channels = {i: None for i in range(inputs[0])}
        self.output_channels = {i: None for i in range(inputs[0])}

        if parameters and 'pid' in parameters:
            self.master_pid = parameters['pid']

    # Assign the queue to the input/output channels
    def set_input(self, id, queue):
        self.input_channels[id] = comm.Channel(id_channel=id, queue=queue)

    def set_output(self, id, queue):
        self.output_channels[id] = comm.Channel(id_channel=id, queue=queue)

    # Create unwired channels
    def init_free_channels(self):
        for (id, c) in self.input_channels.items():
            if c is None:
                self.input_channels[id] = comm.Channel(id_channel=id)

        for (id, c) in self.output_channels.items():
            if c is None:
                self.output_channels[id] = comm.Channel(id_channel=id)

    # Wire two vertex by the channels' ids
    def wire(self, output, vertex, input):
        c = Queue()
        self.set_output(output, c)
        vertex.set_input(input, c)


# Stateless box: transductor, inductor or reductor.
class Box(Vertex):
    def __init__(self, inputs, outputs, box_function, parameters=None):
        super(Box, self).__init__(inputs, outputs, parameters)
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
    def __init__(self, inputs, outputs, box_function, parameters=None):

        # Intuctor has a single input and one or more outputs
        assert(inputs[0] == 1 and inputs[0] >= 1)

        super(Transductor, self).__init__(inputs, outputs, box_function,
                                          parameters)

    def protocol(self):

        msg = None

        while True:
            msg = self.input_channels[0].get()
            assert(isinstance(msg, comm.Message))

            if not msg.is_segmark():
                # Cast the content of the message to the input type if
                # possible, raise an exception otherwise.

                try:
                    input_data = types.cast_message(self.function.passport[0],
                                                    msg.content)

                except types.TypeError as err:
                    print("Type error: " + str(err))

                    # Kill the whole group of threads
                    os.killpg(self.master_pid, signal.SIGTERM)
                    return

                # Evaluate the core function in the input data
                output_data = self.function.run(input_data)

                # Send the result to the output channel. Note that there's
                # no need to cast the output message: if its type appears to be
                # wrong, an exception will be raised by the consumer.
                self.output_channels[0].put(comm.DataMessage(output_data))

            else:
                # Segmentation marks are transferred as is through transductor
                self.outputs_channels[0].put(msg)


# Combination of a pure box function and its passport.
class BoxFunction:
    def __init__(self, function, passport):
        self.passport = passport
        self.run = function
