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
        # Check if there's an input message.
        ready = False
        for port in self.inputs:
            if not port['queue'].is_empty():
                ready |= True

        if not ready:
            return False

        # Check availability of outputs.
        for port in self.outputs:
            assert port['to'] is not None
            if port['to'].is_full():
                return False

        return True

    ##
    ## Methods that are specific for boxes
    ## TODO: consider moving to separate class
    ##

    n_output_msgs = 0

    def send_out(self, mapping):
        for port_id, content in mapping.items():
            out_msg = comm.DataMessage(content)
            self.outputs[port_id]['to'].put(out_msg)
            self.n_output_msgs += 1

    def put_back(self, port_id, data):
        self.inputs[0]['queue'].put_back(comm.DataMessage(data))
        self.n_output_msgs += 1

    def msg_count(self):
        n = self.n_output_msgs
        self.n_output_msgs = 0
        return n


class Transductor(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(Transductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):
        input_channel = self.inputs[0]['queue']

        if input_channel.is_empty():
            return None

        m = input_channel.get()

        return {'vertex_id': self.id, 'args': [m.content]}

    def commit(self, response):
        if response.action == 'send':
            # Send output messages.
            n_output_msgs = self.send_out(response.out_mapping)
        else:
            print(response.action, 'is not implemented yet for ', vertex.name)

        return self.msg_count()


class Printer(Transductor):
    '''
    Temporary class of vertex, just for debugging
    '''

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

        return {'vertex_id': self.id, 'args': [m.content]}

    def commit(self, response):

        if response.action == 'continue':

            cont = response.aux_data
            # Put the continuation back to the input queue
            self.put_back(0, cont)

            self.send_out(response.out_mapping)

        elif response.action == 'terminate':
            n_output_msgs = self.send_out(response.out_mapping)

        else:
            print(response.action, 'is not implemented yet for ', vertex.name)

        return self.msg_count()

###########################

import copy

# Box functions

def printer(d):
    print(d)
    return ('send', {}, None)

def foo(n):
    n += 1
    return ('send', {0: {'value': n, 'n': 10}}, None)

def cnt(s):
    if s['n'] == 0:
        return ('terminate', {}, None)

    time.sleep(2)
    cont = copy.copy(s)
    cont['value'] += 1
    cont['n'] -= 1

    return ('continue', {0: s['value']}, cont)

###########################


if __name__ == '__main__':

    # Processing pool
    pm = pool.PoolManager(2)
    pm.start()

    # Components
    b1 = Transductor('b1', ['in1'], ['out1'], foo)
    b2 = Inductor('b2', ['in2'], ['out2'], cnt)
    b3 = Printer('b3', ['in3'], ['out3'], printer)
    n1 = Net('net', ['global_in'], ['global_out'], [b1, b1], "")

    # Statical wiring
    b1.outputs[0]['to'] = b2.inputs[0]['queue']
    b2.outputs[0]['to'] = b3.inputs[0]['queue']

    # Construct test network

    box_ids = []

    n = Network()

    box_ids.append(n.add_vertex(b1))
    box_ids.append(n.add_vertex(b2))
    box_ids.append(n.add_vertex(b3))

    root_id = n.add_net(n, box_ids)
    n.set_root(root_id)

    # Number of messages wainting for processing in queues.
    # TODO: must be a class variable in Network.
    n_enqueued = 0

    # Initial message
    b1.inputs[0]['queue'].put(comm.DataMessage(10))
    n_enqueued += 1

    # Network execution

    while True:
        # Traversal
        nodes = nx.dfs_postorder_nodes(n.network, n.root)

        for node_id in nodes:
            node = n.node(node_id)

            if node['type'] == 'net':
                # Skip: we are interested in boxes only.
                continue

            elif node['type'] == 'vertex':
                vertex = node['obj']

                # Check if the vertex can be executed.
                # TODO: it would be better if the condition was never true.
                if not vertex.is_ready():
                    continue

                # Get input message.
                data = vertex.fetch()

                # Send core function and data from input msg to processing pool.
                # NOTE: this call MUST always be non-blocking.
                pm.enqueue(vertex.core, data)
                n_enqueued -= 1

        # Check for responses from processing pool.
        while True:
            try:
                # Wait responses from the pool if there're no other messages in
                # queues to process.
                need_block = (n_enqueued == 0)

                if need_block:
                    print("NOTE: no messages in queues, wait for some result")

                # Vertex response.
                response = pm.out_queue.get(need_block)

                if not n.is_in(response.vertex_id):
                    raise ValueError('Vertex corresponsing to the response does'
                                     'not exist.')

                vertex = n.node(response.vertex_id)['obj']

                # Commit the result of computation, e.g. send it to destination
                # vertices.
                n_outputs = vertex.commit(response)
                n_enqueued += n_outputs

            except Empty:
                break

    # Cleanup.
    pm.finish()
