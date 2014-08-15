#!/usr/bin/env python3

from queue import Empty as Empty

import pool
import communication as comm

import re
import time
import collections
import networkx as nx

##############################################


class Network:

    def __init__(self):
        self.network = nx.DiGraph()
        self.root = None
        self.node_id = 0

        # Traversal schedule: only vertices that are ready for execution.
        self.schedule = None
        self.trigger_ports = None

    def node(self, node_id):
        return self.network.node[node_id]

    def add_net(self, net, node_ids):
        net_id = self.node_id
        self.node_id += 1

        net.id = net_id
        self.network.add_node(net_id, {'type': 'net', 'obj': net})

        # Collect components of the net as predesessors.
        for n in node_ids:
            self.network.add_edge(net_id, n)
        return net_id

    def add_vertex(self, vertex):
        vertex_id = self.node_id
        self.node_id += 1

        vertex.id = vertex_id
        self.network.add_node(vertex_id, {'type': 'vertex', 'obj': vertex})

        return vertex_id

    def is_in(self, node_id):
        return (node_id in self.network)

    ##################################

    def set_root(self, node_id):
        self.root = node_id


class Node:
    def __init__(self, name, inputs, outputs):
        self.id = None
        self.name = name

        # Ports of the node itselt
        self.inputs = [{'name': n, 'queue': None} for n in inputs]
        self.outputs = [{'name': n, 'to': None} for n in outputs]

    @property
    def n_inputs(self):
        return len(self.inputs)

    @property
    def n_outputs(self):
        return len(self.outputs)


class Net(Node):
    def __init__(self, name, inputs, outputs, nodes, wiring_expr):
        super(Net, self).__init__(name, inputs, outputs)

        # Mapping from channel names to ports. It is filled during the
        # netlist construction.
        self.ports_naming = {}

        # Mapping from nodes' names to ids in global network graph.
        self.nodes_mapping = self.extract_nodes_mapping(nodes)

        # Netlist of the net is built from the wiring expression and a list of
        # net constituents objects.
        self.netlist = self.build_netlist(nodes, wiring_expr)
        self.wire_id = 0

    def build_netlist(self, nodes, wiring_expr):
        pass

    def extract_nodes_mapping(self, nodes):
        pass


class Vertex(Node):
    def __init__(self, name, inputs, outputs):
        super(Vertex, self).__init__(name, inputs, outputs)

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
        '''
        raise NotImplemented('The `is_ready\' method is not defined for the '
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
        ready = False
        for port in self.inputs:
            if not port['queue'].is_empty():
                ready |= True

        if not ready:
            return False

        # Test availability of outputs.
        if not self.output_available():
            return False

        return True

    ##
    ## Methods that are specific for boxes
    ## TODO: consider moving to separate class
    ##

    # Flag indicating that the box is processing another message.
    busy = False

    def send_out(self, mapping, wrap=True):
        for port_id, content in mapping.items():

            if wrap:
                out_msg = comm.DataMessage(content)
            else:
                out_msg = content

            self.outputs[port_id]['to'].put(out_msg)

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


class Transductor(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(Transductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):
        input_channel = self.inputs[0]['queue']

        if input_channel.is_empty():
            return None

        m = input_channel.get()

        if m.is_segmark():
            # Special behaviour for segmentation marks.
            self.send_to_all(m)
            return None

        else:
            return {'vertex_id': self.id, 'args': [m.content]}

    def commit(self, response):
        if response.action == 'send':
            # Send output messages.
            self.send_out(response.out_mapping)
        else:
            print(response.action, 'is not implemented yet for ', vertex.name)


class Printer(Transductor):
    '''
    Temporary class of vertex, just for debugging
    '''

    def fetch(self):
        input_channel = self.inputs[0]['queue']

        # TODO: To revise: strange sanity check: fetch() is run only if there
        # ARE msgs in the input channel.
        if input_channel.is_empty():
            return None

        m = input_channel.get()

        return {'vertex_id': self.id, 'args': [m.content]}

    def is_ready(self):
        # Check if there's an input message.
        ready = False
        for port in self.inputs:
            if not port['queue'].is_empty():
                ready |= True

        return ready


class Inductor(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(Inductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):
        input_channel = self.inputs[0]['queue']

        if input_channel.is_empty():
            return None

        m = input_channel.get()

        if m.is_segmark():
            # Special behaviour for segmentation marks.
            m.plus()
            self.send_to_all(m)
            return None

        else:
            return {'vertex_id': self.id, 'args': [m.content]}

    def commit(self, response):

        if response.action == 'continue':

            cont = response.aux_data
            # Put the continuation back to the input queue
            self.put_back(0, cont)

            self.send_out(response.out_mapping)

        elif response.action == 'terminate':
            self.send_out(response.out_mapping)

        else:
            print(response.action, 'is not implemented yet for ', vertex.name)


class DyadicReductor(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(DyadicReductor, self).__init__(name, inputs, outputs)
        self.core = core

    def is_ready(self):

        ## Test input availability.
        #

        # Reduction start: 2 messages from both channel are needed.
        for port in self.inputs:
            if port['queue'].is_empty():
                return False

        ## Test output availability.
        #
        if not self.output_available(range(1, self.n_outputs)):
            return False

        # Test the 1st output separately since it must have enough space
        # for segmentation mark.
        if not self.output_available((0,), space_needed=2):
            return False

        return True

    def fetch(self):
        init_terms = self.inputs[0]['queue']
        other_terms = self.inputs[1]['queue']

        # Sanity check. TODO: revise.
        if init_terms.is_empty() or other_terms.is_empty():
            return None

        # First reduction operard:
        term_a = init_terms.get()
        if term_a.is_segmark():
            # Special behaviour for segmentation marks.
            term_a.plus()
            self.send_to_range(term_a, range(1, self.n_outputs), wrap=False)
            return None

        # Second reduction operand
        term_b = other_terms.get()
        if term_b.is_segmark():
            # Special behaviour for segmentation marks.
            self.send_out({0: term_a}, wrap=False)

            if term_b.n != 1:
                if term_b.n > 1:
                    term_b.minus()
                self.send_out({0: term_b}, wrap=False)

        # Input messages are not segmarks: pass them to coordinator.
        return {'vertex_id': self.id, 'args': [term_a.content, term_b.content]}

    def commit(self, response):

        if response.action == 'partial':
            # First output channel cannot be the destination of partial result.
            assert(0 not in response.out_mapping)
            self.send_out(response.out_mapping)

            # Put partial reduction result to the first input channel for
            # further reduction.
            self.put_back(0, response.aux_data)

        else:
            print(response.action, 'is not implemented yet for ', vertex.name)

###########################

import copy

# Box functions

def printer(d):
    print(d)
    return ('send', {}, None)

def foo(n):
    n += 1
    return ('send', {0: {'value': n, 'n': 10}}, None)

def plus(a, b):
    c = a + b
    return ('partial', {}, c)

def cnt(s):
    if s['n'] == 0:
        return ('terminate', {}, None)

    #time.sleep(2)
    cont = copy.copy(s)
    cont['value'] += 1
    cont['n'] -= 1

    return ('continue', {0: s['value']}, cont)

###########################

def n_enqueued(nodes):
    '''
    Count the number of messages waiting for processing in inputs queues of the
    given nodes.
    It's temporary and expensive alternative to network schedule.
    '''
    n_msgs = 0

    for node_id in nodes:
        node = n.node(node_id)
        if node['type'] != 'vertex':
            continue
        vertex = node['obj']

        for q in vertex.inputs:
            n_msgs += q['queue'].size()

    return n_msgs


if __name__ == '__main__':

    # Processing pool
    pm = pool.PoolManager(2)
    pm.start()

    # Components
    b1 = Transductor('b1', ['in1'], ['out1'], foo)
    b2 = Inductor('b2', ['in2'], ['out2'], cnt)
    bR = DyadicReductor('bR', ['inits', 'terms'], ['out'], plus)
    b3 = Printer('b3', ['in3'], ['out3'], printer)
    n1 = Net('net', ['global_in'], ['global_out'], [b1, b1], "")

    # Statical wiring
    b1.outputs[0]['to'] = b2.inputs[0]['queue']
    b2.outputs[0]['to'] = bR.inputs[1]['queue']
    bR.outputs[0]['to'] = b3.inputs[0]['queue']

    # Construct test network

    box_ids = []

    n = Network()

    box_ids.append(n.add_vertex(b1))
    box_ids.append(n.add_vertex(b2))
    box_ids.append(n.add_vertex(b3))
    box_ids.append(n.add_vertex(bR))

    root_id = n.add_net(n, box_ids)
    n.set_root(root_id)

    # Number of messages wainting for processing in queues.
    # TODO: must be a class variable in Network.

    # Initial message
    b1.inputs[0]['queue'].put(comm.DataMessage(1))
    b1.inputs[0]['queue'].put(comm.SegmentationMark(1))
    bR.inputs[0]['queue'].put(comm.DataMessage(0))

    # Network execution

    while True:
        # Traversal
        nodes = list(nx.dfs_postorder_nodes(n.network, n.root))

        for node_id in nodes:
            node = n.node(node_id)

            if node['type'] == 'net':
                # Skip: we are interested in boxes only.
                continue

            elif node['type'] == 'vertex':
                vertex = node['obj']

                if vertex.busy:
                    continue

                # Check if the vertex can be executed.
                # TODO: it would be better if the condition was never true.
                if not vertex.is_ready():
                    continue

                # Get input message.
                data = vertex.fetch()

                if data is None:
                    # Input messages happend to not require the box execution.
                    continue

                # Send core function and data from input msg to processing pool.
                # NOTE: this call MUST always be non-blocking.
                pm.enqueue(vertex.core, data)
                vertex.busy = True

        # Check for responses from processing pool.

        while True:
            try:
                # Wait responses from the pool if there're no other messages in
                # queues to process.
                need_block = (n_enqueued(nodes) == 0)

                if need_block:
                    print("NOTE: waiting result")

                # Vertex response.
                response = pm.out_queue.get(need_block)

                if not n.is_in(response.vertex_id):
                    raise ValueError('Vertex corresponsing to the response does'
                                     'not exist.')

                vertex = n.node(response.vertex_id)['obj']

                # Commit the result of computation, e.g. send it to destination
                # vertices.
                vertex.commit(response)
                vertex.busy = False

            except Empty:
                break

    # Cleanup.
    pm.finish()
