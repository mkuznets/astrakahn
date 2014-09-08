#!/usr/bin/env python3

import collections


class Channel:
    def __init__(self, capasity=0):
        self.queue = collections.deque()
        self.capasity = capasity

    def put(self, m):
        if self.capasity and len(self.queue) >= self.capasity:
            raise IndexError('Queue is full')
        else:
            self.queue.append(m)

    def put_back(self, m):
        self.queue.appendleft(m)

    def get(self):
        if len(self.queue) == 0:
            raise Empty('Queue is empty')
        return self.queue.popleft()

    def is_space_for(self, n):
        if not self.capasity:
            return True

        return True if len(self.queue) + n <= self.capasity else False

    def is_full(self):
        return True if self.capasity and len(self.queue) >= self.capasity\
            else False

    def is_empty(self):
        return True if len(self.queue) == 0 else False

    def size(self):
        return len(self.queue)

    def pressure(self):
        if not self.capasity:
            # Unpressurised channel
            return 0
        else:
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

    def __init__(self, n=None, brackets=None):
        # Number of opening and closing brakets.
        if n is not None:
            self.n = n
        elif brackets is not None:
            closing = False
            n = 0
            nb = 0
            for c in brackets:
                if c == ')' and not closing:
                    nb += 1
                elif c == '(' and not closing:
                    n = nb
                    nb -= 1
                    closing = True
                elif c == '(' and closing:
                    nb -= 1
                else:
                    raise ValueError('Wrong sequence of brackets.')

            if nb != 0:
                raise ValueError('Wrong sequence of brackets.')

            self.n = n

        self.content = self.__repr__()

    def is_segmark(self):
        return True

    def plus(self):
        if self.n > 0:
            self.n += 1
        self.content = self.__repr__()

    def minus(self):
        if self.n > 0:
            self.n -= 1
        else:
            raise ValueError('Negative sequence depth.')
        self.content = self.__repr__()

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


class Empty(Exception):
    def __init__(self, value):
        self.value = value
