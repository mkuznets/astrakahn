#!/usr/bin/env python3

from multiprocessing import Queue, Event, Lock


class Channel:
    """
    AstraKahn channel
    """

    def __init__(self, depth=0, queue=None):
        self.queue = Queue() if not queue else queue

        # The counter and `ready_any' flag are shared among all input channels
        # of a vertex. Counter shows the number of messages received by all
        # input channels. If it becomes, zero, `ready_any' is cleared.
        # They are used only in synchronisers and other special types of
        # vertices and thus can be omitted for usual boxes.
        self.input_cnt = None
        self.ready_any = None

        # Check if the channel involved as an input channel of one of the boxes
        self.input_sync = lambda: bool(self.ready_any) and bool(self.input_cnt)

        # Indicates that the channel is ready.
        self.ready = Event()

        # The flag is set if the number of messages exceeds the critical
        # pressure.
        self.unblocked = Event()
        self.unblocked.set()

        # Parameters of the channel
        self.depth = depth
        self.critical_pressure = 10

        self.me = Lock()

    def get(self, wait_ready=True):
        """
        Get a message from the channel
        """
        if wait_ready:
            self.wait_ready()

        self.me.acquire()

        was_critical = self.is_critical()

        # Last message - channel is not ready for reading
        if self.pressure() == 1:
            if self.input_sync():
                with self.input_cnt.get_lock():
                    self.input_cnt.value -= 1
                    if not self.input_cnt.value:
                        self.ready_any.clear()
            if self.ready.is_set():
                self.ready.clear()

        msg = self.queue.get()

        # Pressure goes down - channel is unlocked
        if was_critical:
            self.unblocked.set()

        self.me.release()
        return msg

    def put(self, msg):
        """
        Put a message to the channel
        """
        self.me.acquire()

        p_before = self.pressure()

        # Pressure is critical now - channel is blocked.
        if (self.pressure() + 1) == self.critical_pressure:
            self.unblocked.clear()

        self.queue.put(msg)

        # The only message in the channel - channel is ready for reading
        if p_before == 0:
            if self.input_sync():
                with self.input_cnt.get_lock():
                    self.input_cnt.value += 1
                    self.ready_any.set()
            self.ready.set()

        self.me.release()
        return

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

    def wait_blocked(self):
        self.unblocked.wait()

    def wait_ready(self):
        self.ready.wait()

    def is_empty(self):
        return self.queue.empty()

    def is_critical(self):
        return self.pressure() >= self.critical_pressure


class Message:
    """
    Superclass of all types of messages
    """

    def end_of_stream(self):
        return False

    def is_segmark(self):
        """
        The message is considered to be a data message by default rather than
        a segmentation mark.
        """
        return False

    def is_empty(self):
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
        self.empty = False
        self.content = self.__repr__()

    def is_segmark(self):
        return True

    def is_empty(self):
        return self.empty

    def end_of_stream(self):
        return True if (self.n == 0) else False

    def set_empty(self):
        self.n = -1
        self.empty = True

    def increment(self):
        if self.n > 0:
            self.n += 1
        self.content = self.__repr__()

    def decrement(self):
        if self.n > 1:
            self.n -= 1
        elif self.n == 1:
            self.set_empty()
        self.content = self.__repr__()

    def __repr__(self):
        if self.n > 0:
            return (")" * self.n) + ("(" * self.n)
        else:
            return "sigma_0"

    def __str__(self):
        return self.__repr__()


class DataMessage(Message):
    """
    Regular data messages
    """

    def __init__(self, content):
        # TODO: not sure at the moment about the type of content.
        self.content = content

    def __repr__(self):
        return "msg(" + str(self.content) + ")"

    def __str__(self):
        return self.__repr__()
