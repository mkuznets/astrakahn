#!/usr/bin/env python3

import communication as comm


class Node:
    def __init__(self, name, inputs, outputs):
        self.id = None
        self.name = name

        # Ports of the node itselt
        self.inputs = [{'name': n, 'queue': None, 'node_id': None}
                       for n in inputs]
        self.outputs = [{'name': n, 'to': None, 'node_id': None}
                        for n in outputs]

    @property
    def n_inputs(self):
        return len(self.inputs)

    @property
    def n_outputs(self):
        return len(self.outputs)


class Net(Node):
    def __init__(self, name, inputs, outputs):
        super(Net, self).__init__(name, inputs, outputs)


class Vertex(Node):

    def __init__(self, name, inputs, outputs):
        super(Vertex, self).__init__(name, inputs, outputs)

        self.state = 0

        # Initialize input queues.
        for p in self.inputs:
            p['queue'] = comm.Channel()

        # Vertex function that is applied to the input messages.
        self.core = None

        self.arrivals = []
        self.departures = []

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
        input_ready = False
        for port in self.inputs:
            input_ready |= (not port['queue'].is_empty())

        # Test availability of outputs.
        output_ready = self.output_available()

        return (input_ready, output_ready)

    ##
    ## Methods that are specific for boxes
    ## TODO: consider moving to separate class
    ##

    # Flag indicating that the box is processing another message.
    busy = False

    def send_out(self, mapping, wrap=True):

        for port_id, content in mapping.items():
            out_msg = comm.DataMessage(content) if wrap else content
            port = self.outputs[port_id]

            port['to'].put(out_msg)
            self.departures.append(port['node_id'])

    def send_to_range(self, msg, rng, wrap=True):
        mapping = {i: msg for i in rng}
        self.send_out(mapping, wrap)

    def send_to_all(self, msg, wrap=False):
        rng = range(self.n_outputs)
        self.send_to_range(msg, rng, wrap)

    def output_available(self, rng=None, space_needed=1):
        if rng is None:
            rng = range(self.n_outputs)

        for port_id in rng:
            if not self.outputs[port_id]['to'].is_space_for(space_needed):
                return False

        return True

    def put_back(self, port_id, data):
        self.inputs[0]['queue'].put_back(comm.DataMessage(data))

    def get(self, port_id):

        if port_id < 0 or port_id >= self.n_inputs:
            raise IndexError('Wrong number of input port.')

        port = self.inputs[port_id]

        m = port['queue'].get()
        self.arrivals.append(port['node_id'])

        return m

    def collect_impact(self):
        impact = (self.departures, self.arrivals)
        self.departures = []
        self.arrivals = []

        return impact


class Transductor(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(Transductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):

        m = self.get(0)

        if m.is_segmark():
            # Special behaviour: sengmentation marks are sent through.
            self.send_to_all(m)
            return None

        else:
            return [m.content]

    def commit(self, response):

        if response.action == 'send':
            # Send output messages.
            self.send_out(response.out_mapping)
        else:
            print(response.action, 'is not implemented.')


class Printer(Transductor):
    '''
    Temporary class of vertex, just for debugging
    '''

    def fetch(self):
        m = self.get(0)
        return [m.content]

    def is_ready(self):

        if self.busy:
            return (False, False)

        # Check if there's an input message.
        input_ready = False
        for port in self.inputs:
            input_ready |= (not port['queue'].is_empty())

        return (input_ready, True)


class Inductor(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(Inductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):
        m = self.get(0)

        if m.is_segmark():
            # Special behaviour for segmentation marks.
            m.plus()
            self.send_to_all(m)
            return None

        else:
            return [m.content]

    def commit(self, response):

        if response.action == 'continue':

            cont = response.aux_data

            # Put the continuation back to the input queue
            self.put_back(0, cont)

            self.send_out(response.out_mapping)

        elif response.action == 'terminate':
            self.send_out(response.out_mapping)

        else:
            print(response.action, 'is not implemented.')


class DyadicReductor(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(DyadicReductor, self).__init__(name, inputs, outputs)
        self.core = core

    def is_ready(self):

        ## Test input availability.
        #

        # Reduction start: 2 messages from both channel are needed.
        input_ready = True
        for port in self.inputs:
            input_ready &= (not port['queue'].is_empty())

        ## Test output availability.
        #

        output_ready = self.output_available(range(1, self.n_outputs))
        # Test the 1st output separately since it must have enough space
        # for segmentation mark.
        output_ready &= self.output_available((0,), space_needed=2)

        return (input_ready, output_ready)

    def fetch(self):

        # First reduction operand:
        term_a = self.get(0)

        if term_a.is_segmark():
            # Special behaviour for segmentation marks.
            term_a.plus()
            self.send_to_range(term_a, range(1, self.n_outputs), wrap=False)
            return None

        # Second reduction operand
        term_b = self.get(1)

        if term_b.is_segmark():
            # Special behaviour for segmentation marks.
            self.send_out({0: term_a}, wrap=False)

            if term_b.n != 1:
                if term_b.n > 1:
                    term_b.minus()
                self.send_out({0: term_b}, wrap=False)

            return None

        # Input messages are not segmarks: pass them to coordinator.
        return [term_a.content, term_b.content]

    def commit(self, response):

        if response.action == 'partial':
            # First output channel cannot be the destination of partial result.
            assert(0 not in response.out_mapping)
            self.send_out(response.out_mapping)

            # Put partial reduction result to the first input channel for
            # further reduction.
            self.put_back(0, response.aux_data)

        else:
            print(response.action, 'is not implemented.')


class Copier(Vertex):

    def __init__(self, name, inputs, outputs, core=None):
        super(Copier, self).__init__(name, inputs, outputs)

    def fetch(self):
        for i in range(self.n_inputs):
            try:
                m = self.get(i)
                self.send_to_all(m)

            except comm.Empty:
                continue
        return None
