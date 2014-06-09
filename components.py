#!/usr/bin/env python3

import os
import sys
import signal

from multiprocessing import Process, Queue, Event, JoinableQueue
from queue import Empty as Empty

import communication as comm
#import typesystem as types

import collections
from random import sample
import logging

import copy
import time

logging.basicConfig(stream=sys.stderr, level=logging.ERROR)


class Vertex:
    """
    Abstract AstraKahn vertex can be either a box or a syncroniser.
    """

    def __init__(self, n_inputs, n_outputs, parameters=None):

        self.inputs = {i: None for i in range(n_inputs)}
        self.outputs = {i: None for i in range(n_outputs)}

        # The boolean flag is shared among all input channels and indicates the
        # presence of message in at least one channel.
        # It is up to the coordinator to assign the flag to each input channel.
        self.input_ready = Event()
        self.input_ready.clear()

        self.process_functions = []
        self.processes = []

        # PID of the master process. It is used for killing the whole network.
        self.master_pid = os.getpid()

    def set_input(self, cid, channel):
        """
        Assign given queue to the input channel
        """
        self.inputs[cid] = channel

    def set_output(self, cid, channel):
        """
        Assign given queue to the output channel
        """
        self.outputs[cid] = channel

    def kill_network(self):
        """
        Stop the whole thread network by killing the master (parent) process
        whose PID is written to each box.
        """
        assert(self.master_pid)
        os.killpg(self.master_pid, signal.SIGTERM)

    ##
    ## Communication methods
    ##

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

    def wait_blocked_outputs(self, channel_range=None):
        """
        Check availability of output channels and waits if any of the output
        channels is blocked.

        Args:
            channel_range: Optional range of indexes of the output channels.
                The argument is useful in reductor when it needs to check only
                some of the output channels (namely, all except for the 1st).
        """
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

        self.inputs[cid].wait_ready()
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
            logger.warning("Box has no running processes to join.")

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


class Transductor(Box):
    """
    Transductor is an AstraKahn box that responds with no more than one output
    message on each of its output channels.

        * One input and at least one output
        * Segmentation bypassed unamended to all outputs
    """
    def __init__(self, n_inputs, n_outputs, core, n_cores=1, passport=None):
        # Transductor has a single input and one or more outputs.
        assert(n_inputs == 1 and n_outputs >= 1)
        super(Transductor, self).__init__(n_inputs, n_outputs, core, passport)

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
        self.input_buffers = [Queue(maxsize=1)
                              for i in range(self.n_cores)]
        self.output_buffer = Queue()

        self.segmark_received = Event()
        self.segmark_received.clear()

        # The queue is owned by router and enables direct communication between
        # merger and router. It is also used by coordinator to signal the
        # router to spawn given number of cores.
        self.control = Queue()

        # Function for initial box running.
        self.process_functions = [self.router, self.merger]

    def spawn(self, n):
        if n > 0:
            self.control.put((-1, 'spawn', n))
            self.logger.debug("Request for %d cores sent to the router", n)
        else:
            raise ValueError("Number of cores must be positive.")

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

    def update_cores(self):
        n_active_cores = len(self.active_cores)

        # It's needed to spawn more cores.
        if n_active_cores < self.n_cores:
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
            self.logger.debug("Killing excess cores: %d running, %d requested",
                              n_active_cores, self.n_cores)

            # Send termination signals to excess cores.
            # TODO: how to choose the cores to kill correctly? It seems
            # that we need to consider a combination of currend load and
            # processing rate from collected statictics.
            # Current solution: random cores.
            for i in range(n_active_cores - self.n_cores):
                #bid = sample(self.active_cores, 1)[0]
                bid = self.release_core_id()
                self.input_buffers[bid].put({'msg': comm.SegmentationMark(0)})
                self.logger.debug("Killing requested: BID: %d", bid)

    def router(self):
        logger = logging.getLogger('router')

        # The flag indicates that the router has received a termination signal
        # and is about to stop execution and waiting for the active cores to
        # finish their tasks.
        is_idle = False

        # Initial core spawning.
        self.update_cores()

        # Input message counter within the segment i.e. between brakets.
        n_seg = 0
        # Input message counter within the box.
        mid = 0

        while True:
            ## Control queue processing
            while True:
                try:
                    # Blocked if is_idle is set since the only thing to do
                    # in this state is waiting for finish feedback from merger.
                    (bid, action, value) = self.control.get(block=(is_idle))

                    # A core has finished.
                    if action == 'finish':
                        logger.debug("Core has finished, BID: %d", bid)

                        # The BID can be released by `update_cores'
                        # TODO: seems like a flaw in case of killing by
                        # `update_cores' - why do the core has to send a
                        # feedback?
                        if bid in self.active_cores:
                            self.release_core_id(bid)

                        # If shutdown flag is set and all cores finished,
                        # router sends termination signal to merger and stops.
                        if is_idle and len(self.active_cores) == 0:
                            logger.debug("No more cores, send stopping request"
                                         " to the merger and exit. Good-bye!")
                            self.output_buffer.put({'type': 'exit'})
                            return

                    # Update the number of running cores.
                    elif action == 'spawn':
                        if is_idle:
                            logger.warning("Spawn request is REFUSED: the box "
                                           "is going to die waiting remaining "
                                           "cores to complete.")
                        else:
                            print("New number of cores:", value)
                            self.n_cores = value
                            self.update_cores()
                    else:
                        raise ValueError("Wrong action")

                except Empty:
                    break

            ## Message processing
            # TODO: `wait_outputs' MUST BE TRUE in the final version.
            msg = self.get_message(cid=0, wait_outputs=False)

            if msg.end_of_stream():
                # Move to idle-state and broadcast the end-of-stream to all
                # active cores
                is_idle = True
                for bid in self.active_cores:
                    self.input_buffers[bid].put({'msg': msg, 'mid': mid})
                continue

            elif msg.is_segmark():
                self.output_buffer.put({'type': 'segmark', 'depth': msg.n,
                                        'mid': mid, 'n_seg': n_seg})
                self.segmark_received.wait()
                n_seg = 0
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
                n_seg += 1

    def merger(self):
        logger = logging.getLogger('merger')

        n_seg = n_seg_full = segmark_mid = segmark_depth = 0

        data_buffer = list()
        read_buffer = False
        wait_segment = False

        ##########################################

        def release_segmark(depth, mid):
            """
            Send out pending closing mark, reset segment markers and enable
            reading of data from the nternal queue.
            """
            nonlocal n_seg, read_buffer, data_buffer, wait_segment
            handle_result(msg=comm.SegmentationMark(depth), mid=mid)
            n_seg = 0
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
                    print(result.keys() - self.outputs.keys())
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

                if n_seg == data['n_seg']:
                    release_segmark(depth=data['depth'], mid=data['mid'])
                else:
                    segmark_depth = data['depth']
                    segmark_mid = data['mid']
                    n_seg_full = data['n_seg']
                    wait_segment = True

                self.segmark_received.set()

            elif data['type'] == 'datamsg':
                n_seg += 1
                handle_result(result=data['result'], mid=data['mid'])

                # The whole segment was processed - send the segmark.
                if wait_segment and n_seg == n_seg_full:
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
    def __init__(self, n_inputs, n_outputs, core, passport):
        # Inductor has a single input and one or more outputs
        assert(n_inputs == 1 and n_outputs >= 1)
        super(Inductor, self).__init__(n_inputs, n_outputs, core, passport)

        # Function for initial box running.
        self.process_functions = [self.core_wrapper]

    def core_wrapper(self):
        msg = None
        continuation = None
        consecutive_msg = False

        while True:
            msg = self.get_message(cid=0, wait_outputs=False)\
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



