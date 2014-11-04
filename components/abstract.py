#!/usr/bin/env python3

import communication as comm


class Node:
    def __init__(self, name, inputs, outputs):
        self.id = None
        self.name = name

        self.arrivals = []
        self.departures = []

        # Ports of the node itselt
        self.inputs = [{'id': i, 'name': n, 'queue': None, 'src': None, 'mnt': False}
                       for i, n in enumerate(inputs)]
        self.outputs = [{'id': i, 'name': n, 'to': None, 'dst': None, 'mnt': False}
                        for i, n in enumerate(outputs)]

    @property
    def n_inputs(self):
        return len(self.inputs)

    @property
    def n_outputs(self):
        return len(self.outputs)

    def send_out(self, mapping):

        for port_id, msg in mapping.items():
            port = self.outputs[port_id]

            port['to'].put(msg)
            self.departures.append(port['dst'])

    def send_to_range(self, msg, rng):
        mapping = {i: msg for i in rng}
        self.send_out(mapping)

    def send_to_all(self, msg):
        rng = range(self.n_outputs)
        self.send_to_range(msg, rng)

    def input_ready(self, rng=None, any_channel=True):
        '''
        Returns True if there's a msg in at least one channel from the range.
        '''
        if rng is None:
            rng = range(self.n_inputs)

        input_ready = True

        for port_id in rng:
            queue = self.inputs[port_id]['queue']

            ready = not queue.is_empty()

            if ready and any_channel:
                return True
            else:
                input_ready &= ready

        return input_ready

    def output_ready(self, rng=None, space_needed=1):
        if rng is None:
            rng = range(self.n_outputs)

        for port_id in rng:
            to_queue = self.outputs[port_id]['to']

            if to_queue is None or not to_queue.is_space_for(space_needed):
                return False

        return True

    def get(self, port_id):
        if port_id < 0 or port_id >= self.n_inputs:
            raise IndexError('Wrong number of input port.')

        port = self.inputs[port_id]

        m = port['queue'].get()
        self.arrivals.append(port['src'])

        return m

    def put(self, port_id, msg):
        self.inputs[port_id]['queue'].put(msg)

    def put_back(self, port_id, msg):
        self.inputs[port_id]['queue'].put_back(msg)

    def collect_impact(self):
        impact = (self.departures, self.arrivals)
        self.departures = []
        self.arrivals = []

        return impact


class Net(Node):
    def __init__(self, name, inputs, outputs):
        super(Net, self).__init__(name, inputs, outputs)

    def copy(self):
        inputs = [p['name'] for p in self.inputs]
        outputs = [p['name'] for p in self.outputs]
        return self.__class__(self.name, inputs, outputs)


class Vertex(Node):

    def __init__(self, name, inputs, outputs):
        super(Vertex, self).__init__(name, inputs, outputs)

        # Initialize input queues.
        for p in self.inputs:
            p['queue'] = comm.Channel()

        # Vertex function that is applied to the input messages.
        self.core = None

        # Flag indicating that the box is processing another message.
        self.busy = False

    # TODO: the method is run on the assumption that is_ready() returned True,
    # this creates undesirable logical dependence between these methods.
    def fetch(self):
        '''
        Fetch required number of message(s) from input queue(s) and return the
        data in the form suitable for processing pool.
        '''
        raise NotImplemented('The fetch method is not defined for the '
                             'abstract vertex.')

    def commit(self):
        '''
        Handle the result received from processing pool. Return the number of
        output messages sent.
        '''
        raise NotImplemented('The commit method is not defined for the '
                             'abstract vertex.')

    def is_ready(self):
        '''
        Check if the condition on channels are sufficient for the vertex to
        start.

        NOTE: The very implementation applies for common types of vertices that
        need (1) at least one message on one of the inputs (2) all outputs to
        be available.
        '''
        # Test if there's an input message.
        input_ready = self.input_ready()

        # Test availability of outputs.
        output_ready = self.output_ready()

        return (input_ready, output_ready)

    def copy(self):
        inputs = [p['name'] for p in self.inputs]
        outputs = [p['name'] for p in self.outputs]
        return self.__class__(self.name, inputs, outputs, self.core)


class Box(Vertex):
    pass
