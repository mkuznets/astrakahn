#!/usr/bin/env python3

import os
import sys
import signal

from multiprocessing import Process, Queue, Event, Value
from queue import Empty as Empty

import communication as comm
#import typesystem as types

import collections
from random import sample
import logging

import copy
import time
import math

logging.basicConfig(stream=sys.stderr)  # , level=logging.DEBUG)


class Vertex:
    """
    Abstract AstraKahn vertex can be either a box or a syncroniser.
    """

    def __init__(self, n_inputs, n_outputs, parameters=None):

        self.inputs = {i: None for i in range(n_inputs)}
        self.outputs = {i: None for i in range(n_outputs)}

        # The counter and ready flag are shared among all input channels
        # of a vertex. Counter shows the number of messages received by all
        # input channels. If it becomes, zero, ready flag is cleared by
        # .get() method of a channel, and vice-versa, ready flag is set when
        # the counter is > 0.
        # The primitives allow a vertex to wait for a message on any of the
        # input channel without expensive polling each of them.
        self.input_cnt = Value('i')
        self.input_ready = Event()
        self.input_ready.clear()

        self.process_functions = []
        self.processes = []

        self.logger = logging.getLogger("Vertex")

    ## Communication methods.
    ##

    def set_input(self, cid, channel):
        """
        Assign given queue to the input channel
        """
        self.inputs[cid] = channel
        self.inputs[cid].ready_any = self.input_ready
        self.inputs[cid].input_cnt = self.input_cnt

    def set_output(self, cid, channel):
        """
        Assign given queue to the output channel
        """
        self.outputs[cid] = channel

    def ready_inputs(self, channel_range=None):
        """
        Args:
            channel_range: sequence of input channel ids
        """
        if not channel_range:
            channel_range = range(len(self.inputs))

        ready_list = [cid for cid in channel_range
                      if not self.inputs[cid].is_empty()]

        return ready_list

    def is_output_blocked(self, channel_range=None):
        """
        Args:
            channel_range: sequence of output channel ids

        Returns:
            True -- at least one is blocked.
            False -- all channels are available for output.
        """
        if not channel_range:
            channel_range = range(len(self.outputs))

        for cid in channel_range:
            if self.outputs[cid].is_blocked():
                return True

        return False

    def wait_any_input(self):
        self.input_ready.wait()

    def wait_blocked_outputs(self, channel_range=None):
        """
        Check availability of output channels and waits if any of the output
        channels is blocked.

        Args:
            channel_range: Optional range of indexes of the output channels.
                The argument is useful in reductor when it needs to check only
                some of the output channels (namely, all except for the 1st).
        """
        if not self.outputs:
            return

        if not channel_range:
            channel_range = range(len(self.outputs))

        for cid in channel_range:
            self.outputs[cid].wait_blocked()

    def get_message(self, cid, wait_outputs=True):
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

        if wait_outputs:
            self.wait_blocked_outputs()

        msg = self.inputs[cid].get()

        return msg

    def put_message(self, msg, cids=None, wait_outputs=False):
        # TODO: Not quite sure if it is needed here.
        if wait_outputs:
            self.wait_blocked_outputs()

        # Putting operation
        put = lambda cid, msg: self.outputs[cid].put(msg)

        # Every channel
        if cids is None:
            for cid in self.outputs.keys():
                put(cid, msg)

        # Single channel
        elif type(cids) == int:
            put(cids, msg)

        # Specified range of channels
        elif isinstance(cids, collections.Iterable):
            for cid in cids:
                put(cid, msg)

    ## Execution control methods.
    ##

    def start(self):
        if self.process_functions:
            for f in self.process_functions:
                p = Process(target=f)
                p.start()
                self.processes.append(p)
        else:
            raise NotImplementedError("The concrete box implementation must "
                                      "specify a list of process functions in "
                                      "order to be able to run")

    def join(self):
        if self.processes:
            for p in self.processes:
                p.join()
        else:
            self.logger.warning("Box has no running processes to join.")

    def stop(self):
        raise NotImplementedError("")


class Box(Vertex):

    def __init__(self, n_inputs, n_outputs, core, passport):
        super(Box, self).__init__(n_inputs, n_outputs)
        self.core = core
        self.passport = passport

        self.impl_name = self.__class__.__name__
        self.logger = logging.getLogger(self.impl_name)

    def spawn(self, n):
        raise NotImplementedError("")


class ProliferativeBox(Box):
    def __init__(self, n_inputs, n_outputs, core, n_cores=1, passport=None,
                 buffer_size=1):
        super(ProliferativeBox, self).__init__(n_inputs, n_outputs, core,
                                               passport)

        # (Maximum) number of parallel cores of the box.
        self.n_cores = n_cores

        # Running core IDs
        self.active_cores = list()
        # List of core IDs available to run.
        self.core_slots = list(range(self.n_cores))

        # Initially the number of core IDs is equal to the given maximum number
        # of cores (IDs starting from 0).
        self.id_core_max = n_cores - 1

        # Input and output buffers for cores.
        self.input_buffers = [Queue(maxsize=buffer_size)
                              for i in range(self.n_cores)]
        self.output_buffer = Queue()

        # The queue is owned by router and enables direct communication between
        # merger and router. It is also used by coordinator to signal the
        # router to spawn given number of cores.
        self.control = Queue()

        # The flag indicates that the router has received a termination signal
        # and is about to stop execution and waiting for the active cores to
        # finish their tasks.
        self.is_idle = False

        self.segmark_received = Event()
        self.segmark_received.clear()

    def control_queue_reader(self):

        while True:
            try:
                # Blocked if is_idle is set since the only thing to do
                # in this state is waiting for finish feedback from merger.
                control_msg = self.control.get(block=(self.is_idle))

                ret = self.control_handler(control_msg)
                if ret is None:
                    ret = 0

                if ret > 0:
                    return ret
                elif ret < 0:
                    raise ValueError("Wrong action")

            except Empty:
                break
        return 0

    def update_cores(self):
        n_active_cores = len(self.active_cores)

        if n_active_cores < self.n_cores:
            # Spawn more cores.

            self.logger.debug("Spawning new cores: %d running, %d requested",
                              n_active_cores, self.n_cores)

            # Allocate new queues and slots if needed.
            if (self.n_cores - 1) > self.id_core_max:
                id_range = range(self.id_core_max + 1, self.n_cores)
                self.core_slots += list(id_range)
                self.input_buffers += [Queue(maxsize=1) for i in id_range]
                self.id_core_max = self.n_cores - 1

                self.logger.debug("Allocated new core slots: %d running, "
                                  "%d requested", n_active_cores, self.n_cores)

            # Spawn cores.
            for i in range(self.n_cores - n_active_cores):
                bid = self.acquire_core_id()
                core_process = Process(target=self.core_wrapper, args=(bid,))
                core_process.start()
                self.logger.debug("NEW core: BID: %d, PID: %d", bid,
                                  core_process.pid)

        elif n_active_cores > self.n_cores:
            # Kill excess cores.

            self.logger.debug("Killing excess cores: %d running, %d requested",
                              n_active_cores, self.n_cores)

            # Send termination signals to excess cores.
            # TODO: how to choose the cores to kill correctly? It seems
            # that we need to consider a combination of currend load and
            # processing rate from collected statictics.
            # Current solution: random cores.
            for i in range(n_active_cores - self.n_cores):
                bid = self.release_core_id()
                self.input_buffers[bid].put({'msg': comm.SegmentationMark(0)})
                self.logger.debug("Killing requested: BID: %d", bid)

    def spawn(self, n):
        if n > 0:
            self.control.put((-1, 'spawn', n))
            self.logger.debug("Request for %d cores sent to the router", n)
        else:
            raise ValueError("Number of cores must be positive.")

    def acquire_core_id(self):
        bid = self.core_slots.pop()
        self.active_cores.append(bid)
        return bid

    def release_core_id(self, bid=-1):
        if bid < 0:
            bid = self.active_cores.pop()
        else:
            self.active_cores.remove(bid)
        self.core_slots.append(bid)
        return bid


class Transductor(ProliferativeBox):
    """
    Transductor is an AstraKahn box that responds with no more than one output
    message on each of its output channels.

        * One input and at least one output
        * Segmentation bypassed unamended to all outputs
    """
    def __init__(self, n_inputs, n_outputs, core, n_cores=1):
        # Transductor has a single input and one or more outputs.
        assert(n_inputs == 1 and n_outputs >= 1)
        super(Transductor, self).__init__(n_inputs, n_outputs, core, n_cores,
                                          None, 1)

        # Function for initial box running.
        self.process_functions = [self.router, self.merger]

    def control_handler(self, control_msg):
        (bid, action, value) = control_msg

        # A core has finished.
        if action == 'finish':
            self.logger.debug("Core has finished, BID: %d", bid)

            # The BID can be already released by `update_cores'.
            if bid in self.active_cores:
                self.release_core_id(bid)

            # If shutdown flag is set and all cores finished, router sends
            # termination signal to merger and stops.
            if self.is_idle and len(self.active_cores) == 0:
                self.logger.debug("No more cores, send stopping request"
                                  " to the merger and exit. Good-bye!")
                self.output_buffer.put({'type': 'exit'})
                return 1

        # Update the number of running cores.
        elif action == 'spawn':
            if self.is_idle:
                self.logger.warning("Spawn request is REFUSED: the box "
                                    "is going to die waiting remaining "
                                    "cores to complete.")
            else:
                print("New number of cores:", value)
                self.n_cores = value
                self.update_cores()
        else:
            return -1

    def router(self):
        logger = logging.getLogger('router')

        # Initial core spawning.
        self.update_cores()

        # Input message counter within the segment i.e. between brakets.
        msg_n = 0
        # Input message counter within the box.
        mid = 0

        while True:
            ## Control queue processing
            ret = self.control_queue_reader()
            if ret > 0:
                return

            ## Message processing
            msg = self.get_message(cid=0)

            if msg.end_of_stream():
                # Move to idle-state and broadcast the end-of-stream to all
                # active cores
                self.is_idle = True
                for bid in self.active_cores:
                    self.input_buffers[bid].put({'msg': msg, 'mid': mid})
                continue

            elif msg.is_segmark():
                self.output_buffer.put({'type': 'segmark', 'depth': msg.n,
                                        'mid': mid, 'msg_n': msg_n})
                self.segmark_received.wait()
                self.segmark_received.clear()
                msg_n = 0
                mid += 1

            else:
                # Select a suitable core for the new message.
                # TODO: this problem is also need to be considered in terms
                # of load and processing rate!

                # Less Busy First Algorithm
                free_cores = {bid: self.input_buffers[bid].qsize()
                              for bid in self.active_cores}
                free_sort = sorted(free_cores, key=free_cores.get)
                bid = free_sort[0]

                self.input_buffers[bid].put({'msg': msg, 'mid': mid})
                mid += 1
                msg_n += 1

    def core_wrapper(self, bid):
        logger = logging.getLogger('core_wrapper_#' + str(bid))

        # Working input buffer.
        input_buffer = self.input_buffers[bid]

        while True:
            data = input_buffer.get()
            msg = data['msg']

            if msg.end_of_stream():
                logger.debug("End-of stream received, send feedback to merger "
                             "end exit. Good-bye!")
                data['type'] = 'end-of-stream'
                data['bid'] = bid
                self.output_buffer.put(data)
                return

            else:
                # Only data messages and end-of-stream are sent to cores.
                assert(not msg.is_segmark())

                logger.debug("%s received.", str(msg))

                # Evaluate the core function on the input data.
                result = self.core(msg.content)

                logger.debug("Result for %s computed. Sending to merger...",
                             str(msg))

                result_data = {'type': 'datamsg', 'result': result,
                               'mid': data['mid'], 'bid': bid}
                self.output_buffer.put(result_data)

    def merger(self):
        logger = logging.getLogger('merger')

        msg_n = msg_n_full = segmark_mid = segmark_depth = 0

        data_buffer = list()
        read_buffer = False
        wait_segment = False

        ##########################################

        def release_segmark(depth, mid):
            """
            Send out pending closing mark, reset segment markers and enable
            reading of data from the nternal queue.
            """
            nonlocal msg_n, read_buffer, data_buffer, wait_segment
            handle_result(msg=comm.SegmentationMark(depth), mid=mid)
            msg_n = 0
            read_buffer = True
            wait_segment = False
            data_buffer = sorted(data_buffer, key=lambda x: x['mid'],
                                 reverse=True)

        def handle_result(result=None, msg=None, mid=-1):

            if result is not None:
                # Result as a mapping to different outputs.
                if type(result) != dict:
                    raise ValueError("Result mapping to outputs must be given"
                                     "as a dictionary!")
                if (result.keys() - self.outputs.keys()):
                    raise ValueError("Wrong output channels given")

                for (cid, data) in result.items():
                    output_msg = comm.DataMessage(data)
                    self.put_message(output_msg, cid)

                logger.info("Result for MID: %d: %s", mid,
                            str(result))

            elif msg is not None:
                # Result as a single message to all outputs.
                if not isinstance(msg, comm.Message):
                    raise ValueError("Type of the given message is wrong!")

                self.put_message(msg)

                logger.info("Result for MID: %d: %s", mid,
                            str(msg))

            else:
                # Empty output
                pass

        ##########################################

        while True:
            #self.wait_blocked_outputs()

            # Reading from internal buffer.
            if read_buffer and len(data_buffer) > 0:

                if wait_segment and data_buffer[-1]['mid'] > segmark_mid:
                    read_buffer = False
                    logger.debug("Stop reading from buffer: too recent data.")
                    continue

                data = data_buffer.pop()
                logger.debug("Read a data from buffer: MID: %d.", data['mid'])

                if len(data_buffer) == 0:
                    read_buffer = False
                    logger.debug("Stop reading from buffer: buffer's empty.")

            # Reading from the main control queue.
            else:
                data = self.output_buffer.get()

                if wait_segment and data.get('mid', 0) > segmark_mid:
                    data_buffer.append(data)
                    logger.debug("Add to buffer: MID: %d.", data['mid'])
                    continue

            if data['type'] == 'segmark':
                # If the whole segment was processed - send out the segmark,
                # otherwise store the expected lenght of segment and pending
                # the segmark until the end of the segment.

                if msg_n == data['msg_n']:
                    release_segmark(depth=data['depth'], mid=data['mid'])
                else:
                    segmark_depth = data['depth']
                    segmark_mid = data['mid']
                    msg_n_full = data['msg_n']
                    wait_segment = True

                self.segmark_received.set()

            elif data['type'] == 'datamsg':
                msg_n += 1
                handle_result(result=data['result'], mid=data['mid'])

                # The whole segment was processed - send the segmark.
                if wait_segment and msg_n == msg_n_full:
                    release_segmark(depth=segmark_depth, mid=segmark_mid)

            elif data['type'] == 'end-of-stream':
                # Provide feedback to the router that the core has stopped.
                logger.debug("Received end-of-stream, BID: %d", data['bid'])
                self.control.put((data['bid'], 'finish', -1))
                continue

            elif data['type'] == 'exit':
                # Router has stopped. Send end-of-stream forward and exit.
                logger.debug("Going to exit. Good-bye!")
                handle_result(msg=comm.SegmentationMark(0))
                return

            else:
                raise ValueError("Type of data is wrong: " + str(data['type']))


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
    def __init__(self, n_inputs, n_outputs, core):
        # Inductor has a single input and one or more outputs.
        assert(n_inputs == 1 and n_outputs >= 1)
        super(Inductor, self).__init__(n_inputs, n_outputs, core,
                                       passport=None)

        # Function for initial box running.
        self.process_functions = [self.core_wrapper]

        # Messages that are sent to the input right after the start.
        self.initial_messages = []

    def core_wrapper(self):
        msg = None
        continuation = None
        consecutive_msg = False

        # Send initial messages to itself.
        if self.initial_messages:
            self.inputs[0].wait_blocked()
            for m in self.initial_messages:
                self.inputs[0].put(m)

        while True:
            msg = self.get_message(cid=0)\
                if not continuation else comm.DataMessage(continuation)

            if not msg.is_segmark():

                if consecutive_msg and not continuation:
                    # Put a segmentation mark between consecutive messages
                    self.put_message(comm.SegmentationMark(1))

                consecutive_msg = True

                # Evaluate the core function in the input data
                result, continuation = self.core(msg.content)

                # If function returns None, output is considered to be empty
                if result is None:
                    continue

                # Send the result (except for `continuation') to outputs
                for (cid, data) in result.items():
                    output_msg = comm.DataMessage(data)
                    self.put_message(output_msg, cid)

            else:
                consecutive_msg = False

                # Segmentation marks are transferred through inductor with
                # incremented depth.
                output_msg = copy.copy(msg)
                output_msg.increment()
                self.put_message(output_msg)

                if msg.end_of_stream():
                    return


class Reductor(ProliferativeBox):
    def __init__(self, n_inputs, n_outputs, core, n_cores=1, ordered=False,
                 segmentable=True):
        # Reductor has 1 or 2 inputs and one or more outputs
        assert((n_inputs == 1 or n_inputs == 2) and n_outputs >= 1)

        super(Reductor, self).__init__(n_inputs, n_outputs, core, n_cores,
                                       None, 0)

        self.monadic = True if (n_inputs == 1) else False
        self.ordered = ordered
        self.segmentable = segmentable

        self.feedback = Queue()

        # Dyadic reduction cannot be done in parallel except for special cases
        # that are not yet considered. In monadic case only non-segmentable
        # reductor cannot proliferate.
        self.non_proliferative = (not self.monadic) or (self.ordered and
                                                        not self.segmentable)

        self.term_channel = 0 if self.monadic else 1

        if self.non_proliferative and self.n_cores > 1:
            self.n_cores = 1
            self.logger.warning("Ordered non-segmentable reductor does not "
                                "support proliferation, reset the number of "
                                "cores to 1")
        self.seg_len = 2

        self.process_functions = [self.router]

    def control_handler(self, control_msg):
        (bid, action, value) = control_msg

        # A core has finished.
        if action == 'finish':
            self.logger.debug("Core has finished, BID: %d", bid)

            # The BID can be already released by `update_cores'.
            if bid in self.active_cores:
                self.release_core_id(bid)

            # If shutdown flag is set and all cores finished,
            # router sends termination signal to merger and stops.
            if self.is_idle and len(self.active_cores) == 0:
                self.logger.debug("No more cores, send stopping request "
                                  "to the merger and exit. Good-bye!")

                self.put_message(comm.SegmentationMark(0))
                return 1

        # Update the number of running cores.
        elif action == 'spawn':
            if self.is_idle:
                self.logger.warning("Spawn request is REFUSED: the box is "
                                    "going to die waiting remaining cores to "
                                    "complete.")
            elif value > 1 and self.non_proliferative:
                self.logger.warning("Spawn request is REFUSED: reductor "
                                    "is ordered and non-segmentable.")
            else:
                self.n_cores = value
                self.update_cores()
                self.logger.debug("New number of cores: " + str(value))

        # Update the lenght of reduction segment.
        elif action == 'segment':
            if self.non_proliferative:
                self.logger.warning("Request is REFUSED: reductor is ordered "
                                    "and non-segmentable.")
            else:
                self.seg_len = value
                self.logger.debug("New lenght of segment: " + str(value))
        else:
            return -1

    def router(self):

        def core_assign(n, p):
            # Generate task distribution.
            s = int(n / p)
            r = n - s * p
            d = [s] * (p - 1)
            rnd = sample(range(p-1), r)

            for i in rnd:
                d[i] += 1
            d.append(-1)

            return d

        def release_segmark(started, segmark):
            if started:
                segmark.decrement()
                if not segmark.is_empty():
                    self.put_message(segmark, 0)
                    logger.info(str(segmark) + " to the 1st channel")
            elif not started:
                segmark.increment()
                logger.info(str(segmark) + " to channels > 1")
                self.put_message(segmark, range(1, len(self.outputs)))

        logger = logging.getLogger('router')

        # Initial core spawning.
        self.update_cores()

        segmark_buffer = None

        reduction_started = False
        processing = False
        next_reduction_step = False

        cbid = 0
        msg_n = 0

        core_sched = core_assign(self.seg_len, self.n_cores)

        # Though messages are distributed to all available cores, there can be
        # a case when the number of messages is less than the number of cores.
        # Because of this the variable track the number of cores used in a
        # given step of reduction.
        n_cores_used = set([0])

        tasks = collections.deque()

        while True:
            ## Control queue processing
            if self.control_queue_reader() > 0:
                return

            ## Message processing
            if tasks:
                msg = tasks.popleft()
            else:
                cid = self.term_channel if reduction_started else 0
                msg = self.get_message(cid)

            if msg.is_segmark():
                # Segmentation mark

                if not processing:
                    # Two cases are possible:
                    #  1. Reductor is waiting for the first term. In this case
                    #     segmarks can be either from the 1st or 2nd channel.
                    #  2. Reductor has performed a reduction and is about to
                    #     send a segmark after the result.
                    # In both cases segmarks are processed immediately.

                    if msg.end_of_stream():
                        self.is_idle = True
                        for bid in self.active_cores:
                            self.input_buffers[bid].put({'type': 'stop'})
                    else:
                        release_segmark(reduction_started, msg)

                    # If a reduction has taken place, it considered to be
                    # completed after this step.
                    reduction_started = False

                else:
                    # Reduction is performing, segmark can only be from the 2nd
                    # channel, it delimits lists of terms.

                    if self.ordered:
                        # In ordered case a sequence of messages is divided
                        # into segments of known lenght, therefore at the end
                        # of it we should put end-of-list mark to the last core
                        # only.
                        self.input_buffers[cbid].put({'type': 'end'})

                    else:
                        # In unordered reductor end-of-list are sent only at
                        # the end of message sequence for all used cores at
                        # once.
                        for bid in n_cores_used:
                            self.input_buffers[bid].put({'type': 'end'})

                    segmark_buffer = msg
                    next_reduction_step = True

            else:
                # Data message

                if reduction_started and not processing:
                    # Reduction is already performed, but started flag is still
                    # on. The only thing to do in this state is to yield the
                    # result (the only possible data message in the state).
                    self.put_message(msg, 0)

                else:
                    # Reduction is performing, data message is sent to one of
                    # the cores, either randomly (in unordered reductor)
                    # or by segments of supposedly equal lenght (segmented
                    # ordered reductor).

                    self.input_buffers[cbid].put({'type': 'term', 'msg': msg,
                                                  'n': msg_n})
                    n_cores_used.add(cbid)

                    # Policy of core usage.

                    if self.ordered:
                        if core_sched[cbid] >= 0:
                            core_sched[cbid] -= 1
                            if core_sched[cbid] == 0:
                                self.input_buffers[cbid].put({'type': 'end'})
                                cbid += 1
                    else:
                        cbid = (cbid + 1) % len(core_sched)

                    reduction_started = True
                    processing = True
                    msg_n += 1

            if not next_reduction_step:
                continue

            ## Receive partial result from cores and continue computation.

            n_results = len(n_cores_used)

            intermediate = []

            cnt = n_results
            while cnt:
                r = self.feedback.get()

                if r['type'] == 'result':
                    tasks.append(r)
                    cnt -= 1

                elif r['type'] == 'intermediate':
                    intermediate.append(r)

            if n_results == 1:
                processing = False

            tasks = collections.deque(x['result'] for x in
                                      sorted(tasks, key=lambda x: x['bid']))

            # Intermediate
            intermediate = sorted(intermediate, key=lambda x: x['n'])
            for m in intermediate:
                self.put_message(m['msg'], m['cid'])

            if processing:
                core_sched = core_assign(n_results, math.floor(n_results/2))
            else:
                core_sched = core_assign(self.seg_len, self.n_cores)

            n_cores_used = set([0])
            cbid = 0
            next_reduction_step = False
            tasks.append(segmark_buffer)

    def core_wrapper(self, bid):
        logger = logging.getLogger('core_wrapper_#' + str(bid))

        # Working input buffer.
        input_buffer = self.input_buffers[bid]

        # Protocol loop.
        while True:
            # First element of reduction.
            data = input_buffer.get()

            if data['type'] == 'stop':
                self.control.put((bid, 'finish', -1))
                return

            assert(data['type'] == 'term')

            partial = data['msg']

            # Loop over list to reduce.
            while True:
                data = input_buffer.get()

                if data['type'] == 'term':
                    term = data['msg']

                    # Partial result computation
                    result = self.core(partial.content, term.content)
                    partial = comm.DataMessage(result[0])

                    # Send intermediate values (that depend on computation of
                    # partial result) to all outputs except for the first one.
                    for (cid, content) in result.items():
                        if cid > 0:
                            msg = comm.DataMessage(content)

                            self.feedback.put({'bid': bid,
                                               'type': 'intermediate',
                                               'msg': msg, 'n': data['n'],
                                               'cid': cid})

                elif data['type'] == 'end':
                    self.feedback.put({'bid': bid, 'type': 'result',
                                       'result': partial})
                    break

                else:
                    raise ValueError("Wrong data type")


class Producer(Inductor):

    def __init__(self, n_inputs, n_outputs, core, initial_messages=[]):
        # Inductor has a single input and one or more outputs
        super(Producer, self).__init__(n_inputs, n_outputs, core)

        self.initial_messages = list(initial_messages)
        self.initial_messages.append(comm.SegmentationMark(0))


class Consumer(Box):

    def __init__(self, n_inputs, n_outputs, core):
        # Inductor has a single input and one or more outputs
        super(Consumer, self).__init__(n_inputs, 0, core, None)

        self.process_functions = [self.core_wrapper]

    def core_wrapper(self):
        n_eos = 0
        n_inputs = len(self.inputs)

        while n_eos < n_inputs:
            self.wait_any_input()
            cids = self.ready_inputs()

            for cid in cids:
                msg = self.get_message(cid)
                self.core(cid, msg)

                if msg.end_of_stream():
                    n_eos += 1
