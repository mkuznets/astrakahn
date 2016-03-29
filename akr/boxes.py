def transductor(func):
    def run(channel, msg):
        return func(msg)
    run.cat = 'transductor'
    run.name = func.__name__
    return run


def inductor(func):
    def run(channel, msg):
        return func(msg)
    run.cat = 'inductor'
    run.cont = None
    run.name = func.__name__
    return run


def reductor(ordered):
    def getf(func):
        def run(channel, msg):
            return func(msg)
        run.cat = 'reductor'
        run.cont = None
        run.ordered = ordered
        run.name = func.__name__
        return run
    return getf


def output(func):
    def run(channel, msg):
        return func(channel, msg)
    run.cat = 'output'
    run.name = func.__name__
    return run
