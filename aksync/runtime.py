from typing import Sequence, Tuple
from collections import ChainMap


def extract(msg, pattern, tail=None, depth=None):

    local_vars = {l: msg[l] for l in pattern}

    if tail:
        tail_labels = msg.keys() - set(pattern)
        local_vars[tail] = {l: msg[l] for l in tail_labels if l != '__n__'}

    if depth:
        assert '__n__' in msg
        local_vars[depth] = msg['__n__']

    return local_vars


class State:

    def __init__(self, name: str, **kawrgs):
        self.name = name
        self._variables = kawrgs.copy()

    def scope(self):
        return dict(self._variables)

    def __getitem__(self, name):
        return self._variables[name]

    def __setitem__(self, name, value):
        self._variables[name] = value

    def update(self, new):
        for k in self._variables.keys() & new.keys():
            self._variables[k] = new[k]

    def copy(self):
        return State(self.name, **self._variables)
