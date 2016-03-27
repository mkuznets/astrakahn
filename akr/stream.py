from collections import Sequence, defaultdict
from itertools import chain
from functools import partial
from . import utils


class Stream:
    stream = None
    depth = None
    bc = None
    bmax = None

    def __init__(self):
        self.list_ids = defaultdict(int)
        self.list_idxs = defaultdict(int)

        self.index = 0

    def _clear(self):
        self.bmax = 0
        self.bc = 0
        self.depth = None
        self.stream = []

    def read(self, seq):
        self._clear()

        self._scan(seq)
        s = self.stream

        self.list_ids[0] += 1

        return s

    def _scan(self, stream, level=0):

        assert isinstance(stream, Sequence)

        for item in stream:

            if isinstance(item, Sequence):
                # Nested list

                if self.bc > 0:
                    self.bc -= 1

                if self.bc == 0 and self.bmax > 0:
                    # Bracketing sequence )..)(..( occured

                    self.stream[-1].bracket = self.bmax
                    self.index = 0
                    self.bmax = 0

                self.list_ids[level+1] += 1

                self._scan(item, level+1)

                self.list_idxs[level] += 1

            else:
                # Message

                self.depth = level if self.depth is None else self.depth

                # Make sure messages are only found at the innermost sequence.
                if level != self.depth:
                    raise ValueError('Wrong sequence')

                # Join list identifiers and indicies
                lists = ((self.list_ids[i], self.list_idxs[i])
                         for i in range(level+1))

                # Flatten ids and indicies, remove trailing 0 and insert msg id
                mid = tuple(chain(*lists))[:-1] + (self.index, )

                self.stream.append(
                    Message(item, mid)
                )

                self.index += 1

        for k in filter(lambda x: x > level, self.list_idxs):
            self.list_idxs[k] = 0

        # Exit list
        self.bc += 1
        self.bmax += 1

        if level == 0:
            self.stream[-1].bracket = 0


class Message:

    def __init__(self, content, id, bracket=None):
        self.content = content
        self.id = id

        self.bracket = None
        self.channel = None
        self.pc = None

    def __repr__(self):
        supers = lambda n: ''.join(chr(8304 + int(i)) for i in str(n))
        ss = lambda n: ''.join(chr(8320 + int(i)) for i in str(n))
        return '<M%s,%s%s>' % (ss(self.id[-1]),
                                type(self.content).__name__,
                                ',\u03C3%s' % ss(self.bracket) if self.bracket is not None else '')

    def set_loc(self, channel, pc):
        self.channel = channel
        self.pc = pc

    def id_up(self, port, index):
        pre_id = self.id_eye(port)

        ls = b''.join(map(utils.to_bytes, self.id))
        list_id = utils.md5s(ls, port)

        return pre_id + (list_id, index)

    def id_down(self, port):
        raise NotImplementedError('id_down')

    def id_eye(self, port):
        # - dimension and indicies are the same
        # - update list identifiers
        ids = map(partial(utils.md5i, port), self.id[::2])
        idxs = self.id[1::2]
        return tuple(chain(*zip(ids, idxs)))

    def sm_inc(self, sm_init=-1):
        if sm_init != -1:
            self.bracket = sm_init

        if self.bracket == 0:
            pass

        else:
            self.bracket = (self.bracket or 0) + 1

    def sm_dec(self, sm_init=-1):
        if sm_init != -1:
            self.bracket = sm_init

        if self.bracket == 0 or self.bracket is None:
            pass

        elif self.bracket == 1:
            self.bracket = None

        else:
            self.bracket = self.bracket - 1

    def dump(self):
        return ('msg', self.content, self.id, self.bracket,
                self.channel, self.pc)
