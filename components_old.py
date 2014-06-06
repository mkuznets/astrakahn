#!/usr/bin/env python3

class Inductor(Box):
    """
    Inductor is an AstraKahn box that responds to a single message from the
    input channel with a sequence of messages on each of its output channels.

        * One input and at least one output
        * \sigma_n are bypassed as \sigma_{n+1}, and a \sigma_1 is inserted
          between every two consecutive data messages
        * After each message in a response sequence continuation message is
          Always generated and used in the next iteration, potentially after
          a blockage due to critical pressure in the outputs.
    """
    def __init__(self, n_inputs, n_outputs, function, passport, parameters=None):
        # Inductor has a single input and one or more outputs
        assert(n_inputs == 1 and n_outputs >= 1)

        super(Inductor, self).__init__(n_inputs, n_outputs, function, passport,
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
                    for (id, out_channel) in self.outputs.items():
                        out_channel.put(comm.SegmentationMark(1))

                consecutive_msg = True

                # Evaluate the core function in the input data
                output_data = self.function(msg.content)

                # If function returns None, output is considered to be empty
                if output_data is None:
                    continue

                # Send the result (except for `continuation' to outputs
                for (channel_id, data) in output_data.items():
                    if channel_id != 'continuation':
                        out_msg = comm.DataMessage(data)
                        self.outputs[channel_id].put(out_msg)

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

                for (id, out_channel) in self.outputs.items():
                    out_channel.put(segmark)

                if msg.end_of_stream():
                    return


class Reductor(Box):
    def __init__(self, n_inputs, n_outputs, function, passport, parameters=None):
        # Reductor has 1 or 2 inputs and one or more outputs
        assert((n_inputs == 1 or n_inputs == 2) and n_outputs >= 1)

        super(Reductor, self).__init__(n_inputs, n_outputs, function, passport,
                                       parameters)

        self.monadic = True if (n_inputs == 1) else False
        self.term_channel = 0 if self.monadic else 1

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

                for channel_id in range(1, len(self.outputs)):
                    self.outputs[channel_id].put(segmark)

                if partial_result.end_of_stream():
                    return

                continue

            # Second element of reduction or first element of list of
            #subsequent terms to reduce
            term = self.read_message(self.term_channel)

            # Segmark from the second channel here means that there's only one
            # term to reduce - from the 1st channel. Send it out with a proper
            # segmark.
            if term.is_segmark():
                # Send complete result out
                self.outputs[0].put(partial_result)

                # Choose proper segmark
                if term.n > 1:
                    segmark = comm.SegmentationMark(term.n - 1)
                elif term.n == 0:
                    segmark = comm.SegmentationMark(0)
                else:
                    segmark = None

                # Send the proper segmark
                if segmark:
                    self.outputs[0].put(segmark)

                if term.end_of_stream():
                    return

                continue

            while True:
                # Partial result computation
                output_data = self.function(partial_result.content,
                                                term.content)

                # Send some intermediate values (that may depends on
                # computation of partial result) to all outputs except for the
                # first one.
                for (channel_id, data) in output_data.items():
                    if channel_id > 0:
                        out_msg = comm.DataMessage(data)
                        self.outputs[channel_id].put(out_msg)

                partial_result = comm.DataMessage(output_data[0])

                # These calls are blocked if there's no messages in 2nd input
                # or output channels (except for the 1st one) are blocked.
                term = self.read_message(self.term_channel)
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
            self.outputs[0].put(partial_result)

            # Choose proper segmark
            if term.n > 1:
                segmark = comm.SegmentationMark(term.n - 1)
            elif term.n == 0:
                segmark = comm.SegmentationMark(0)
            else:
                segmark = None

            # Send the proper segmark
            if segmark:
                self.outputs[0].put(segmark)

            if term.end_of_stream():
                return

class Copier(Box):

    def __init__(self, n_inputs, n_outputs, function, passport, parameters=None):
        # Transductor has a single input and one or more outputs
        assert(n_inputs > 0 and n_outputs > 0)

        super(Copier, self).__init__(n_inputs, n_outputs, function, passport,
                                          parameters)

    def protocol(self):
        msg = None
        input_ids = set(self.inputs.keys())

        # Protocol loop
        while True:

            # TODO: make this loop less ugly...
            input_ids_iter = copy.copy(input_ids)

            for input_id in input_ids_iter:

                if not self.inputs[input_id].empty():
                    msg = self.read_message(input_id)

                    if msg.end_of_stream():
                        # Disable the input channel from which end-of-stream
                        # was received.
                        input_ids.remove(input_id)

                        # Don't send end-of-stream if some channels are left.
                        if len(input_ids) > 0:
                            continue

                    # Broadcast the message to all outputs
                    for (output_id, output_ch) in self.outputs.items():
                        output_ch.put(msg)

                    # Exit if no input channels left
                    if len(input_ids) == 0:
                        return

class Synchroniser(Vertex):

    def __init__(self, n_inputs, n_outputs, function, passport, parameters=None):

        # For now -- just a stub since ideally syncroniser class MUST NOT be
        # inherited from the Box.
        # TODO: Fix the inheritance tree ASAP.
        super(Synchroniser, self).__init__(n_inputs, n_outputs, lambda x : x, object,
                                          None)

        self.sync_table = function
        self.state = 'start'

    def protocol(self):
        global_var = {}
        local_var = {}

        # Protocol loop
        while True:

            # Get a set of input channles read in the current state.
            input_set = set(self.sync_table[self.state].keys())

            while len(self.available_inputs(input_set)) == 0:
                self.nonempty_cv.wait()

            # Select an input channel (nondeterministically)
            ch_id = self.available_inputs(input_set)[0]

            print(self.available_inputs(input_set))
            msg = self.read_message(ch_id, False, False)

            transitions = sync_table[self.state][ch_id]

            t_id = None
            pattern_match = False
            choice_match = False

            # Traverse all transitions in the selected group and search a match.
            for t in transitions['group']:

                # Segmentation mark
                if (t['segmark'] is not None) and msg.is_segmark():
                    local_var[t['segmark']] = (None, msg.content,)

                # Pattern matching.
                elif (t['pattern'] is not None) and not msg.is_segmark():
                    try:
                        match = types.cast_message(t['pattern'], msg.content)
                        pattern_match = True


                    except TypeError as mismatch:
                        pattern_match = False

                # TODO: support choices.
                elif t['choice'] is not None:
                    raise NotImplementedError("`choice' datatype is not supported yet")

                else:
                    continue




            self.kill_network()

            if not msg.is_segmark():
                # Evaluate the core function in the input data
                output_data = self.function(msg.content)

                # If function returns None, output is considered to be empty
                if output_data is None:
                    continue

                for (ch, data) in output_data.items():
                    out_msg = comm.DataMessage(data)
                    self.outputs[ch].put(out_msg)

            if msg.end_of_stream():
                return
