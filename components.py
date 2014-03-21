#!/usr/bin/env python3

import communication as comm
from multiprocessing import Process, Queue
import typesystem as types
import os
import signal


class Vertex:
    """
    Abstract AstraKahn vertex can be either a box or a syncroniser.
    """

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

        # PID of the master process. It is used for killing the whole network.
        self.master_pid = os.getpid()

        # TODO
        self.name = ""

    def set_input(self, id, queue):
        """
        Assign given queue to the input channel
        """
        self.input_channels[id] = comm.Channel(id_channel=id, queue=queue)

    def set_output(self, id, queue):
        """
        Assign given queue to the output channel
        """
        self.output_channels[id] = comm.Channel(id_channel=id, queue=queue)

    def init_free_channels(self):
        """
        Create unwired channels
        """
        for (id, c) in self.input_channels.items():
            if c is None:
                self.input_channels[id] = comm.Channel(id_channel=id)
        for (id, c) in self.output_channels.items():
            if c is None:
                self.output_channels[id] = comm.Channel(id_channel=id)

    def wire(self, output, vertex, input):
        """
        Wire two vertex by the channels' ids
        """
        c = Queue()
        self.set_output(output, c)
        vertex.set_input(input, c)

    def kill_network(self):
        """
        Stop the whole thread network by killing the master (parent) process
        whose PID is written to each box.
        """
        assert(self.master_pid)
        os.killpg(self.master_pid, signal.SIGTERM)


class Box(Vertex):
    """
    Stateless box: transductor, inductor or reductor.
    """

    def __init__(self, inputs, outputs, box_function, parameters=None):
        super(Box, self).__init__(inputs, outputs, parameters)
        self.function = box_function

    def start(self):
        """
        Initializes free channels and runs box protocol function in a new
        thread.
        """
        # TODO: the implicit call - possibly poor desigh decision
        self.init_free_channels()

        self.thread = Process(target=self.protocol)
        self.thread.start()

    def stop(self):
        """
        Terminates the box
        """
        self.thread.terminate()

    def protocol(self):
        """
        Virtual method of a box that are executed inside the box
        """
        raise NotImplementedError("Protocol is not implemented.")

    def wait_for_outputs(self, channel_range=None):
        """
        Check availability of output channels and waits if any of the output
        channels is blocked.

        Args:
            channel_range: Optional range of indexes of the output channels.
                The argument is useful in reductor when it needs to check only
                some of the output channels (namely, all except for the 1st).
        """
        if not channel_range:
            channel_range = range(len(self.output_channels))

        for channel_id in channel_range:
            self.output_channels[channel_id].ready.wait()

    def read_message(self, channel_index):
        """
        Get a message (either data one or segmark) from the channel and cast it
        to the input type if possible, kill the whole network of threads
        otherwise.

        Args:
            channel: Index of an input channel

        Returns:
            Input message either casted to the input type or segmark.

        Raises:
            AssertionError: channel index refers to nonexisting channel.
        """

        assert(channel_index >= 0 and channel_index < len(self.input_channels))

        self.wait_for_outputs()

        msg = self.input_channels[channel_index].get()
        assert(isinstance(msg, comm.Message))

        if not msg.is_segmark():
            try:
                input_passport = self.function.passport['input'][channel_index]

                msg.content = types.cast_message(input_passport, msg.content)

            # Inconsistency in types of messages
            except types.TypeError as err:
                print("Type error: " + str(err))
                self.kill_network()
                quit()

        return msg


class Transductor(Box):
    """
    Transductor is an AstraKahn box that responds with no more than one output
    message on each of its output channels.

        * One input and at least one output
        * Segmentation bypassed unamended to all outputs
    """
    def __init__(self, inputs, outputs, box_function, parameters=None):
        # Transductor has a single input and one or more outputs
        assert(inputs[0] == 1 and outputs[0] >= 1)

        super(Transductor, self).__init__(inputs, outputs, box_function,
                                          parameters)

    def protocol(self):
        msg = None

        # Protocol loop
        while True:
            msg = self.read_message(0)

            if not msg.is_segmark():
                # Evaluate the core function in the input data
                output_data = self.function.run(msg.content)

                # If function returns None, output is considered to be empty
                if output_data is None:
                    continue

                for (ch, data) in output_data.items():
                    out_msg = comm.DataMessage(data)
                    self.output_channels[ch].put(out_msg)
            else:
                # Segmentation marks are transferred as is through transductor
                for (channel_id, out_channel) in self.output_channels.items():
                    out_channel.put(msg)

                if msg.end_of_stream():
                    return


class Inductor(Box):
    """
    Inductor is an AstraKahn box that responds to a single message from the
    input channel with a sequence of messages on each of its output channels.

        * One input and at least one output
        * \sigma_n are bypassed as \sigma_{n+1}, and a \sigma_1 is inserted
          between every two consecutive data messages
        * After each message in a response sequence continuation message is
          always generated and used in the next iteration, potentially after
          a blockage due to critical pressure in the outputs.
    """
    def __init__(self, inputs, outputs, box_function, parameters=None):
        # Inductor has a single input and one or more outputs
        assert(inputs[0] == 1 and outputs[0] >= 1)

        super(Inductor, self).__init__(inputs, outputs, box_function,
                                       parameters)

    def protocol(self):
        msg = None
        continuation = None
        consecutive_msg = False

        # Protocol loop
        while True:
            msg = self.read_message(0)\
                if not continuation else comm.DataMessage(continuation)

            if not msg.is_segmark():

                if consecutive_msg and not continuation:
                    # Put a segmentation mark between consecutive messages
                    for (id, out_channel) in self.output_channels.items():
                        out_channel.put(comm.SegmentationMark(1))

                consecutive_msg = True

                # Evaluate the core function in the input data
                output_data = self.function.run(msg.content)

                # If function returns None, output is considered to be empty
                if output_data is None:
                    continue

                # Send the result (except for `continuation' to outputs
                for (channel_id, data) in output_data.items():
                    if channel_id != 'continuation':
                        out_msg = comm.DataMessage(data)
                        self.output_channels[channel_id].put(out_msg)

                if 'continuation' not in output_data:
                    # Absence of `continuation' in the result means that it's
                    # the last element of sequence.
                    continuation = None

                    continue
                else:
                    # Assign `continuation' to be read in the next step.
                    continuation = output_data['continuation']
                    continue

            else:
                consecutive_msg = False

                # Choose a proper segmark
                if msg.n > 0:
                    # Segmentation marks are transferred through inductor with
                    # incremented depth.
                    segmark = comm.SegmentationMark(msg.n + 1)
                elif msg.n == 0:
                    segmark = comm.SegmentationMark(0)

                for (id, out_channel) in self.output_channels.items():
                    out_channel.put(segmark)

                if msg.end_of_stream():
                    return


class Reductor(Box):
    def __init__(self, inputs, outputs, box_function, parameters=None):
        # Reductor has exactly 2 inputs and one or more outputs
        assert(inputs[0] == 2 and outputs[0] >= 1)

        super(Reductor, self).__init__(inputs, outputs, box_function,
                                       parameters)

    def protocol(self):
        partial_result = None
        term = None

        # Protocol loop
        while True:
            # Message from the 1st channel (first element of reduction)
            partial_result = self.read_message(0)

            # Segmark from the first channel bypassed with incremented depth
            if partial_result.is_segmark():

                if partial_result.n > 0:
                    segmark = comm.SegmentationMark(partial_result.n + 1)
                else:
                    segmark = comm.SegmentationMark(0)

                for channel_id in range(1, len(self.output_channels)):
                    self.output_channels[channel_id].put(segmark)

                if partial_result.end_of_stream():
                    return

                continue

            # Message from the 2nd channel (second element of reduction or
            # first element of list of subsequent terms to reduce)
            term = self.read_message(1)

            # Segmark from the second channel here means that there's only one
            # term to reduce - from the 1st channel. Send it out with a proper
            # segmark.
            if term.is_segmark():
                # Send complete result out
                self.output_channels[0].put(partial_result)

                # Choose proper segmark
                if term.n > 1:
                    segmark = comm.SegmentationMark(term.n - 1)
                elif term.n == 0:
                    segmark = comm.SegmentationMark(0)
                else:
                    segmark = None

                # Send the proper segmark
                if segmark:
                    self.output_channels[0].put(segmark)

                if term.end_of_stream():
                    return

                continue

            while True:
                # Partial result computation
                output_data = self.function.run(partial_result.content,
                                                term.content)

                # Send some intermediate values (that may depends on
                # computation of partial result) to all outputs except for the
                # first one.
                for (channel_id, data) in output_data.items():
                    if channel_id > 0:
                        out_msg = comm.DataMessage(data)
                        self.output_channels[channel_id].put(out_msg)

                partial_result = comm.DataMessage(output_data[0])

                # These calls are blocked if there's no messages in 2nd input
                # or output channels (except for the 1st one) are blocked.
                term = self.read_message(1)
                self.wait_for_outputs()

                # Segmark here indicates the end of the term list: stops the
                # computations
                if term.is_segmark():
                    break

            # Protocol reaches this point only at the end of computations, i.e.
            # iff `term' is a segmark.
            # TODO: such control dependency is TOO implicit. Certainly poor
            # design decision.

            # Send complete result out
            self.output_channels[0].put(partial_result)

            # Choose proper segmark
            if term.n > 1:
                segmark = comm.SegmentationMark(term.n - 1)
            elif term.n == 0:
                segmark = comm.SegmentationMark(0)
            else:
                segmark = None

            # Send the proper segmark
            if segmark:
                self.output_channels[0].put(segmark)


class BoxFunction:
    """
    Combination of a pure box function and its passport.
    """
    def __init__(self, function, passport):
        self.passport = passport
        self.run = function
