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
        sent_to = []

        for port_id, content in mapping.items():

            if wrap:
                out_msg = comm.DataMessage(content)
            else:
                out_msg = content

            self.outputs[port_id]['to'].put(out_msg)
            sent_to.append(self.outputs[port_id]['node_id'])

        return sent_to

    def send_to_range(self, msg, rng, wrap=True):
        mapping = {i: msg for i in rng}
        return self.send_out(mapping, wrap)

    def send_to_all(self, msg, wrap=False):
        rng = range(self.n_outputs)
        return self.send_to_range(msg, rng, wrap)

    def output_available(self, rng=None, space_needed=1):
        if rng is None:
            rng = range(self.n_outputs)

        for port_id in rng:
            if not self.outputs[port_id]['to'].is_space_for(space_needed):
                return False

        return True

    def put_back(self, port_id, data):
        self.inputs[0]['queue'].put_back(comm.DataMessage(data))


class Transductor(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(Transductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):
        input_channel = self.inputs[0]['queue']

        fetched_from = []
        sent_to = []

        m = input_channel.get()
        fetched_from.append(self.inputs[0]['node_id'])

        if m.is_segmark():
            # Special behaviour: sengmentation marks are sent through.
            sent_to += self.send_to_all(m)
            return (None, fetched_from, sent_to)

        else:
            return ([m.content], fetched_from, sent_to)

    def commit(self, response):

        sent_to = []

        if response.action == 'send':
            # Send output messages.
            sent_to += self.send_out(response.out_mapping)
        else:
            print(response.action, 'is not implemented.')

        return sent_to


class Printer(Transductor):
    '''
    Temporary class of vertex, just for debugging
    '''

    def fetch(self):
        input_channel = self.inputs[0]['queue']

        fetched_from = []

        # TODO: To revise: strange sanity check: fetch() is run only if there
        # ARE msgs in the input channel.
        if input_channel.is_empty():
            return None

        m = input_channel.get()
        fetched_from.append(self.inputs[0]['node_id'])

        return ([m.content], fetched_from, [])

    def is_ready(self):
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
        input_channel = self.inputs[0]['queue']

        fetched_from = []
        sent_to = []

        if input_channel.is_empty():
            return (None, fetched_from, sent_to)

        m = input_channel.get()
        fetched_from.append(self.inputs[0]['node_id'])

        if m.is_segmark():
            # Special behaviour for segmentation marks.
            m.plus()
            sent_to += self.send_to_all(m)
            return (None, fetched_from, sent_to)

        else:
            return ([m.content], fetched_from, sent_to)

    def commit(self, response):

        sent_to = []

        if response.action == 'continue':

            cont = response.aux_data
            # Put the continuation back to the input queue
            self.put_back(0, cont)
            sent_to.append(self.id)

            sent_to += self.send_out(response.out_mapping)

        elif response.action == 'terminate':
            sent_to += self.send_out(response.out_mapping)

        else:
            print(response.action, 'is not implemented.')

        return sent_to


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
        init_terms = self.inputs[0]['queue']
        other_terms = self.inputs[1]['queue']

        fetched_from = []
        sent_to = []

        # Sanity check. TODO: revise.
        if init_terms.is_empty() or other_terms.is_empty():
            return (None, fetched_from, sent_to)

        # First reduction operand:
        term_a = init_terms.get()
        fetched_from.append(self.inputs[0]['node_id'])

        if term_a.is_segmark():
            # Special behaviour for segmentation marks.
            term_a.plus()
            sent_to += self.send_to_range(term_a, range(1, self.n_outputs),
                                          wrap=False)
            return (None, fetched_from, sent_to)

        # Second reduction operand
        term_b = other_terms.get()

        fetched_from.append(self.inputs[1]['node_id'])

        if term_b.is_segmark():
            # Special behaviour for segmentation marks.
            sent_to += self.send_out({0: term_a}, wrap=False)

            if term_b.n != 1:
                if term_b.n > 1:
                    term_b.minus()
                sent_to += self.send_out({0: term_b}, wrap=False)

            return (None, fetched_from, sent_to)

        # Input messages are not segmarks: pass them to coordinator.
        return ([term_a.content, term_b.content], fetched_from, sent_to)

    def commit(self, response):

        sent_to = []

        if response.action == 'partial':
            # First output channel cannot be the destination of partial result.
            assert(0 not in response.out_mapping)
            sent_to += self.send_out(response.out_mapping)

            # Put partial reduction result to the first input channel for
            # further reduction.
            self.put_back(0, response.aux_data)
            sent_to.append(self.id)

        else:
            print(response.action, 'is not implemented.')

        return sent_to


class Copier(Vertex):

    def __init__(self, name, inputs, outputs, core=None):
        super(Copier, self).__init__(name, inputs, outputs)

    def fetch(self):

        fetched_from = []
        sent_to = []

        for i, port in enumerate(self.inputs):
            if not port['queue'].is_empty():
                input_port = port
                break

        m = input_port['queue'].get()
        fetched_from.append(input_port['node_id'])

        sent_to += self.send_to_all(m)
        return (None, fetched_from, sent_to)

    def commit(self, response):
        # The method was intentionally left blank.
        pass
