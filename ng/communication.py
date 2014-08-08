#!/usr/bin/env python3


class Message:
    """
    Superclass of all types of messages
    """

    def end_of_stream(self):
        return False

    def is_segmark(self):
        return False


class SegmentationMark(Message):

    def __init__(self, n, mid=0):
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

    def __init__(self, content, mid=0):
        self.content = content

    def __repr__(self):
        return "msg(" + str(self.content) + ")"

    def __str__(self):
        return self.__repr__()
