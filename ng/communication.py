#!/usr/bin/env python3

import collections


class Channel:
    def __init__(self, capasity=0):
        self.queue = collections.deque()
        self.capasity = capasity

    def put(self, m):
        if len(self.queue) >= self.capasity:
            raise IndexError('Queue is full')
        else:
            self.queue.append(m)

    def put_back(self, m):
        self.queue.appendleft(m)

    def get(self):
        if len(self.queue) == 0:
            raise IndexError('Queue is empty')
        return self.queue.popleft()

    def is_full(self):
        return True if len(self.queue) >= self.capasity else False

    def is_empty(self):
        return True if len(self.queue) == 0 else False

    def pressure(self):
        return min(len(self.queue), self.capasity)


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
