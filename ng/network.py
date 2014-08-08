#!/usr/bin/env python3

from queue import Empty as Empty

import pool
import communication as comm

import re
import collections
import networkx as nx

##############################################


class Network:

    def __init__(self):
        self.network = nx.DiGraph()
        self.root = None
        self.node_id = 0

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

    ##################################

    def set_root(self, node_id):
        self.root = node_id


class Node:
    def __init__(self, name, inputs, outputs):
        self.id = None
        self.name = name

        # Ports of the node itselt
        self.inputs = [{'name': n, 'queue': None} for n in inputs]
        self.outputs = [{'name': n, 'to': []} for n in outputs]


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
            p['queue'] = collections.deque()

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
        Handle the result received from processing pool.
        '''
        raise NotImplemented('The commit method is not defined for the '
                             'abstract vertex.')


class Transductor(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(Transductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):
        q = self.inputs[0]['queue']

        if len(q) == 0:
            return None

        m = q.popleft()

        return {'vertex_id': self.id, 'args': [m.content]}


###########################

# Box functions


def foo(n):
    n += 1
    return {0: n}

###########################


if __name__ == '__main__':

    # Processing pool
    pm = pool.PoolManager(2)
    pm.start()

    # Components
    b1 = Transductor('b1', ['in1'], ['out1'], foo)
    b2 = Transductor('b2', ['in2'], ['out2'], foo)
    n1 = Net('net', ['global_in'], ['global_out'], [b1, b1], "")

    # Statical wiring
    b1.outputs[0] = [b2.inputs[0]['queue']]

    # Construct test network

    box_ids = []

    n = Network()

    box_ids.append(n.add_vertex(b1))
    box_ids.append(n.add_vertex(b2))

    root_id = n.add_net(n, box_ids)
    n.set_root(root_id)

    # Auxiliary counters
    n_enqueued = 0

    # Initial message
    b1.inputs[0]['queue'].append(comm.DataMessage(10))
    n_enqueued += 1

    # Network execution

    nodes = nx.dfs_postorder_nodes(n.network, n.root)

    for node_id in nodes:
        node = n.node(node_id)

        if node['type'] == 'net':
            # Skip: we are interested in boxes only.
            continue

        elif node['type'] == 'vertex':
            vertex = node['obj']

            # Get data from input message.
            data = vertex.fetch()

            if data is None:
                # Input appeared to be empty.
                # TODO: it is better not to traverse nodes with empty input.
                continue

            # Send core function and data from input msg to processing pool.
            # NOTE: this call MUST always be non-blocking.
            pm.enqueue(vertex.core, data)
            n_enqueued -= 1

    while True:
        try:
            # Wait results from the pool if there're no other messages in
            # queues to process.
            need_block = (n_enqueued == 0)
            r = pm.out_queue.get(need_block)
            print(r)

        except Empty:
            break