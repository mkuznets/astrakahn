def transductor(func):
    def run(channel, msg):
        return func(msg)
    run.cat = 'transductor'
    return run


def inductor(func):
    def run(channel, msg):
        return func(msg)
    run.cat = 'inductor'
    run.cont = None
    return run


def reductor(ordered):
    def getf(func):
        def run(channel, msg):
            return func(msg)
        run.cat = 'reductor'
        run.cont = None
        run.ordered = ordered
        return run
    return getf


def output(func):
    def run(channel, msg):
        return func(channel, msg)
    run.cat = 'output'
    return run
