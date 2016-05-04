from typing import Sequence, Tuple
from collections import ChainMap

class Condition(object):
    def __init__(self):
        pass

    def test(self, msg: dict) -> Tuple[bool, dict]:
        raise NotImplementedError('test() is not implemented')


class ConditionPass(Condition):

    def __init__(self, is_else=False):
        super().__init__()
        self.is_else = bool(is_else)

    def test(self, msg: dict) -> Tuple[bool, dict]:
        return True, {}


class ConditionData(Condition):

    def __init__(self, pattern: Sequence, tail: str):
        super().__init__()
        self.pattern = pattern or ()
        self.tail = tail

    def test(self, msg: dict) -> Tuple[bool, dict]:

        match = all((label in msg) for label in self.pattern)

        if match:
            local_vars = {l: msg[l] for l in self.pattern}

            if self.tail:
                tail_labels = msg.keys() - set(self.pattern)
                local_vars[self.tail] = {l: msg[l] for l in tail_labels}

            return True, local_vars

        else:
            return False, {}


class ConditionSegmark(ConditionData):

    def __init__(self, depth: str, pattern: Sequence, tail: str):
        super().__init__(pattern, tail)
        self.depth = depth

    def test(self, msg: dict) -> Tuple[bool, dict]:

        if '__n__' not in msg:
            return False, {}

        match, local_vars = super().test(msg)

        if match:
            local_vars[self.depth] = msg['__n__']

        return match, local_vars


class State(object):

    def __init__(self, name: str, **kawrgs):
        self.name = name
        self._variables = kawrgs.copy()
        self._locals = {}

    def scope(self):
        return dict(ChainMap(self._locals, self._variables))

    def __getitem__(self, name):
        return ChainMap(self._locals, self._variables)[name]

    def __setitem__(self, name, value):
        if name in self._variables:
            self._variables[name] = value
        else:
            self._locals[name] = value

    @property
    def locals(self):
        return self._locals

    @locals.setter
    def locals(self, variables: dict):
        self._locals = variables.copy()

    def copy(self):
        return State(self.name, **self._variables)
