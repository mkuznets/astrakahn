class Condition(object):
    def __init__(self):
        self.locals = {}

    def test(self, msg=None):
        raise NotImplementedError('test() is not implemented')


class ConditionPass(Condition):

    def __init__(self, is_else=False):
        super(ConditionPass, self).__init__()
        self.is_else = bool(is_else)

    def test(self, msg=None):
        return True


class ConditionData(Condition):

    def __init__(self, pattern=None, tail=None):
        super(ConditionData, self).__init__()

        self.pattern = pattern
        self.tail = tail

    def _match_pattern(self, msg):

        if self.pattern is not None:
            if not all((label in msg) for label in self.pattern):
                return False

            match = msg.extract(self.pattern, self.tail)
            self.locals.update(match)

        return True

    def test(self, msg):
        self.locals.clear()

        if type(msg) is not comm.Record:
            return False

        return self._match_pattern(msg)


class ConditionSegmark(ConditionData):

    def __init__(self, depth, pattern=None, tail=None):
        super(ConditionSegmark, self).__init__(pattern, tail)

        # TODO: typecheck `depth'
        assert(isinstance(depth, str))

        self.depth = depth

    def test(self, msg):
        self.locals.clear()

        if not isinstance(msg, comm.SegmentationMark):
            return False

        match = self._match_pattern(msg)

        if match:
            self.locals[self.depth] = msg.n

        return match


#------------------------------------------------------------------------------


class BaseExp(object):

    def compute(self, scope):
        raise NotImplementedError('compute() is not implemented')

class RecordExp(BaseExp):

    def __init__(self, content=None):

        if content is not None and type(content) is not dict:
            raise TypeError('Record data must be either a dict or None.')

        self.content = content

    def compute(self, scope=None):
        return comm.Record(self.content)

class SegmentationMarkExp(BaseExp):

    def __init__(self, depth_exp):

        if type(depth_exp) is not IntExp:
            raise TypeError('Depth expression must be an IntExp instance.')

        self.depth_exp = depth_exp

    def compute(self, scope):
        depth = self.depth_exp.compute(scope)
        assert(type(depth) is int)

        if depth < 0:
            raise RuntimeError('Depth expression resulted in %d, '\
                               'positive integer expected.' % depth)

        return comm.SegmentationMark(depth)

class DataExp(BaseExp):

    def __init__(self, terms, init=None):

        if not isinstance(terms, Sequence) or isinstance(terms, str):
            raise TypeError('Data expression must be constructed from an '
                            'iterable container of terms.')

        if init is not None and not isinstance(init, BaseExp):
            raise TypeError('Initialisation must be of either None or BaseExp type.')

        for term in terms:
            if not isinstance(term, BaseExp):
                raise TypeError('Terms must be expressions.')

        self.terms = terms
        self.init = init

    def compute(self, scope):

        computed_terms = []

        for term in self.terms:
            cterm = term.compute(scope)

            if not isinstance(cterm, comm.Record):
                err = "Term of DataExp has value of type `%s', message expected" \
                    % type(cterm).__name__
                raise RuntimeError(err)

            computed_terms.append(cterm)

        nseg = len([x for x in computed_terms if type(x) is comm.SegmentationMark])

        if nseg > 1:
            raise RuntimeError('Cannot perform a union of multiple segmentation marks.')

        #---

        if nseg > 0:
            # `0' will be replaced with an actual depth.
            result = comm.SegmentationMark(0)
        else:
            result = comm.Record()

        # Compute union of the terms.
        for cterm in computed_terms:
            result.update(cterm.content)

        if self.init:
            m = self.init.compute(scope)
            m.union(result)
            return m

        else:
            # No cast operator.
            return result


class TermThis(BaseExp):

    def compute(self, scope):

        if '__this__' not in scope:
            raise AssertionError('Currently received message not found in scope.')

        if not isinstance(scope['__this__'], comm.Record):
            raise AssertionError("Type of received message is `%s', Record expected."
                                 % (type(scope['__this__']).__name__))

        return scope['__this__']


class TermVar(BaseExp):

    def __init__(self, var):

        if not isinstance(var, str):
            raise TypeError('Variable name must be a string!')

        self.var = var

    def compute(self, scope):

        if self.var not in scope:
            raise RuntimeError("Variable `%s' not found in scope." % self.var)

        return scope[self.var]


class TermVarExpand(BaseExp):

    def __init__(self, var):

        if not isinstance(var, str):
            raise TypeError('Variable-expand name must be a string!')

        self.var = var

    def compute(self, scope):

        if self.var not in scope:
            raise RuntimeError("Variable `%s' not found in scope." % self.var)

        return comm.Record({self.var: scope[self.var]})


class TermPair(BaseExp):

    def __init__(self, label, exp):

        if not isinstance(label, str):
            raise TypeError('Label must be a string!')

        # More general than allowed by syntax, shouldn't cause
        # anything wrong though.
        if not isinstance(exp, BaseExp):
            raise TypeError('A value of pair must be a term!')

        self.label = label
        self.exp = exp

    def compute(self, scope):

        value = self.exp.compute(scope)

        return comm.Record({self.label: value})


class IntExp(BaseExp):

    def __init__(self, func):

        if not callable(func):
            raise TypeError('Function must be a callable object.')

        if not hasattr(func, 'code'):
            raise ValueError("Function object must have `code' attribute.")

        self.func = func

    def compute(self, scope):

        kwargs = {}

        for arg_name in self.func.__code__.co_varnames:

            if arg_name not in scope:
                raise RuntimeError("Variable `%s' not found in scope." % arg_name)

            arg_value = scope[arg_name]

            if not isinstance(arg_value, int):
                err = [
                    "Error while evaluating: %s" % self.func.code,
                    "Variable `%s' has type `%s', `int' expected"
                    % (arg_name, type(arg_value).__name__),
                ]
                raise RuntimeError("\n".join(err))

            kwargs[arg_name] = arg_value

        return int(self.func(**kwargs))

