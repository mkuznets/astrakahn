#!/usr/bin/env python3

from multiprocessing import Queue, Event


class Channel:
    """
    AstraKahn channel
    """

    def __init__(self, id_channel, name=None, depth=None, queue=None):
        self.queue = Queue() if not queue else queue
        self.ready = Event()
        self.ready.set()

        # Paramaters of the channel
        self.id = id_channel
        self.name = name if name is not None else '_' + str(self.id)
        self.depth = depth
        self.critical_pressure = 10

    def get(self):
        """
        Get a message from the channel
        """

        if not self.is_critical():
            self.ready.set()

        msg = self.queue.get()

        return msg

    def put(self, msg):
        """
        Put a message to the channel
        """

        if self.is_critical():
            self.ready.clear()
        else:
            self.ready.set()

        self.queue.put(msg)

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
