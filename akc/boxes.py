def inductor(n_out):
    def setup(func):
        func.n_in = 1
        func.n_out = n_out
        func.cat = 'inductor'
        def getf():
            return func
        getf.__box__ = True
        return getf
    return setup


def transductor(n_out):
    def setup(func):
        func.n_in = 1
        func.n_out = n_out
        func.cat = 'transductor'
        def getf():
            return func
        getf.__box__ = True
        return getf
    return setup


MONADIC = 1
DIADIC = 2
ORDERED = True
UNORDERED = False


def reductor(adity, ordered, n_out):
    assert adity == 1 or adity == 2
    assert ordered is True or ordered is False

    def setup(func):
        func.n_in = adity
        func.n_out = n_out
        func.ordered = ordered
        func.cat = 'reductor'
        def getf():
            return func
        getf.__box__ = True
        return getf
    return setup
