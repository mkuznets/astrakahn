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


#------------------------------------------------------------------------------


class Message(object):
    """
    Superclass of all types of messages
    """

    def end_of_stream(self):
        return False

    def is_segmark(self):
        return False

    def union(self, msg):
        raise NotImplemented('Union method is not implemented for this type '
                             'of message.')


class NilMessage(Message):

    def __init__(self):
        self.content = None

    def __repr__(self):
        return 'nil()'


class DataMessage(Message):
    """
    Regular data messages
    """

    def __init__(self, content=None):
        self.content = content or {}
        self.alt = ''

    def __repr__(self):
        return "msg(" + str(self.content) + ")"

    def __eq__(self, op):
        return isinstance(op, DataMessage) and self.content == op.content

class Record(DataMessage):

    def __init__(self, content=None):

        if content is None:
            content = {}

        elif type(content) is not dict:
            raise TypeError('Record data must be a dictionary.')

        super(Record, self).__init__(content)

    def union(self, msg):
        # TODO: typecheck
        self.update(msg.content)

    def copy(self):
        content = self.content.copy()
        return self.__class__(content)

    def update(self, content):
        # TODO: typecheck
        # TODO: tests
        self.content.update(content)

    def extract(self, pattern, tail=None):

        if not isinstance(pattern, collections.Iterable) or isinstance(pattern, str):
            raise TypeError('Pattern must be an interable container of labels.')

        for p in pattern:
            if type(p) is not str:
                raise TypeError('Labels for must be strings.')
            if not p:
                raise ValueError('Labels must be non-empty strings.')

        local_vars = {}

        if pattern:
            local_vars.update({l: self.content[l] for l in pattern})

        if tail is not None:

            if type(tail) is not str:
                raise TypeError('Tail label must be string.')

            if not tail:
                raise ValueError('Tail label must be non-empty string.')

            if tail in local_vars:
                raise IndexError('Tail label must not coincide with matched labels.')

            label_diff = self.content.keys() - set(pattern)
            local_vars[tail] = Record({l: self.content[l] for l in label_diff})

        return local_vars

    def __contains__(self, label):
        return label in self.content

    def __getitem__(self, index):
        return self.content[index]

    def __setitem__(self, index, value):
        self.content[index] = value

    def pop(self, index, *args):

        if len(args) > 1:
            raise TypeError('pop expected at most 2 arguments, got %s'
                            % 1 + len(args))

        if index in self.content:
            return self.content.pop(index)

        elif args:
            return args[0]

        else:
            raise IndexError('Label %s not found.' % index)

    def __len__(self):
        return len(self.content)

    def __repr__(self):
        return 'record(%s)' % ', '.join('%s: %s' % (k, v)
                                        for k, v in self.content.items())


class SegmentationMark(Record):

    def __init__(self, n=None, nstr=None):

        if n is None and nstr is None:
            raise ValueError('Depth not provided.')

        super(SegmentationMark, self).__init__()
        self.n = n if n is not None else self._str_to_n(nstr)

    @property
    def n(self):
        assert('__n__' in self)
        return self['__n__']

    @n.setter
    def n(self, x):
        if type(x) is not int:
            raise TypeError('Bracketing depth must be an integer.')

        if x < 0:
            raise ValueError('Bracketing depth must be positive or zero.')

        self['__n__'] = x

    def _str_to_n(self, string):

        if type(string) is not str:
            raise TypeError('Bracketing representation must be a string.')

        if string == '' or string == 'sigma_0':
            return 0

        closing = False
        n = 0
        nb = 0
        for c in string:
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

        return n

    def is_segmark(self):
        return True

    def plus(self):
        if self.n > 0:
            self.n += 1

    def minus(self):
        if self.n > 0:
            self.n -= 1
        else:
            raise ValueError('Negative sequence depth.')

    def end_of_stream(self):
        return self.n == 0

    def extract(self, pattern, tail=None):

        outcome = super(SegmentationMark, self).extract(pattern, tail)

        if tail:
            # Remove system value of depth from the tail.
            outcome[tail].pop('__n__', None)

        return outcome

    def union(self, msg):
        n = self.n
        super(SegmentationMark, self).union(msg)

        # Restore depth.
        self.n = n

    def copy(self):
        content = self.content.copy()
        obj = self.__class__(self.n)
        obj.update(content)
        return obj

    def __repr__(self):
        return (')' * self.n) + ('(' * self.n) if self.n else 'sigma_0'


class Empty(Exception):
    def __init__(self, value):
        self.value = value
