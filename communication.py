#!/usr/bin/env python3

from multiprocessing import Queue, Event, Lock


class Channel:
    """
    AstraKahn channel
    """

    def __init__(self, ready_flag=None, depth=0, queue=None):
        self.queue = Queue() if not queue else queue

        # The flag is shared among all input channels and set if the channel
        # is not empty.
        self.ready = ready_flag

        # The flag is set if the number of messages exceeds the critical
        # pressure.
        self.unblocked = Event()
        self.unblocked.set()

        # Parameters of the channel
        self.depth = depth
        self.critical_pressure = 10

        self.me = Lock()

    def set_ready_flag(self, flag):
        self.ready = flag

    def get(self):
        """
        Get a message from the channel
        """
        self.me.acquire()

        was_critical = self.is_critical()

        # Last message - channel is not ready for reading
        if self.pressure() == 1:
            if self.ready and self.ready.is_set():
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
            if self.ready:
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
        self.content = self.__repr__()

    def is_segmark(self):
        return True

    def end_of_stream(self):
        return True if (self.n == 0) else False

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
