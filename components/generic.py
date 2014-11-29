#!/usr/bin/env python3

import sys
import communication as comm


class NodeVisitor(object):

    def generic_visit(self, node, children):
        pass

    def traverse(self, node):

        children = {}

        if isinstance(node, Net):
            for c_name, c in node.nodes.items():
                outcome = self.traverse(c)
                children[c_name] = outcome

        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, children) if visitor else None


class Node:
    def __init__(self, name, inputs, outputs):
        self.id = None
        self.name = name

        # Ports of the node itselt
        self.inputs = [{'id': i, 'name': n, 'queue': None, 'src': None}
                       for i, n in enumerate(inputs)]
        self.outputs = [{'id': i, 'name': n, 'to': None, 'dst': None}
                        for i, n in enumerate(outputs)]

    @property
    def n_inputs(self):
        return len(self.inputs)

    @property
    def n_outputs(self):
        return len(self.outputs)

    def free_ports(self):
        inputs = {}
        outputs = {}

        for p in self.inputs:
            name = p['name']
            if p['src'] is None:
                inputs[name] = inputs.get(name, []) + [(self.id, p)]

        for p in self.outputs:
            name = p['name']
            if p['dst'] is None:
                outputs[name] = outputs.get(name, []) + [(self.id, p)]

        return (inputs, outputs)


    def show(self, buf=sys.stdout, offset=0):
        lead = ' ' * offset
        buf.write(lead + str(self.id) + '. ' + self.__class__.__name__+ ' <' + self.name + "> ")
        buf.write('(' + ', '.join(p['name'] + (str(p['src']) if p['src'] else '') for p in self.inputs) + ' | ')
        buf.write(', '.join(p['name'] + (str(p['dst']) if p['dst'] else '') for p in self.outputs) + ')')
        buf.write('\n')

        if getattr(self, 'nodes', None):
            for name, node in self.nodes.items():
                node.show(buf, offset=offset+2)


class Net(Node):
    def __init__(self, name, inputs, outputs, nodes):
        super(Net, self).__init__(name, inputs, outputs)

        self.nodes = {n.name: n for n in nodes}


class Vertex(Node):

    def __init__(self, name, inputs, outputs):
        super(Vertex, self).__init__(name, inputs, outputs)

        # Initialize input queues.
        for p in self.inputs:
            p['queue'] = comm.Channel()

        # Flag indicating that the box is processing another message.
        self.busy = False

        self.departures = []

    #--------------------------------------------------------------------------

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

    # TODO: the method is run on the assumption that is_ready() returned True,
    # this creates undesirable logical dependence between these methods.
    def fetch(self):
        '''
        Fetch required number of message(s) from input queue(s) and return the
        data in the form suitable for processing pool.
        '''
        raise NotImplemented('The fetch method is not defined for the '
                             'abstract vertex.')

    def commit(self, response):
        '''
        Handle the result received from processing pool. Return the number of
        output messages sent.
        '''
        raise NotImplemented('The commit method is not defined for the '
                             'abstract vertex.')

    #--------------------------------------------------------------------------

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

    def inputs_available(self):
        port_list = []

        for i, p in enumerate(self.inputs):
            if not p['queue'].is_empty():
                port_list.append(i)

        return port_list

    def output_ready(self, rng=None, space_needed=1):
        if rng is None:
            rng = range(self.n_outputs)

        for port_id in rng:
            to_queue = self.outputs[port_id]['to']

            if to_queue is None or not to_queue.is_space_for(space_needed):
                return False

        return True

    #--------------------------------------------------------------------------

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

    def put_back(self, port_id, msg):
        self.inputs[port_id]['queue'].put_back(msg)

    #--------------------------------------------------------------------------

    def get(self, port_id):
        if port_id < 0 or port_id >= self.n_inputs:
            raise IndexError('Wrong number of input port.')

        port = self.inputs[port_id]

        m = port['queue'].get()

        return m

    def put(self, port_id, msg):
        self.inputs[port_id]['queue'].put(msg)

    #--------------------------------------------------------------------------

class Box(Vertex):
    pass
