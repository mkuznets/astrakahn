#!/usr/bin/env python3

import os
import sys
import networkx as nx

import components

sys.path.insert(0, os.path.dirname(__file__) + '/compiler')
import utils


class Network:

    def __init__(self):
        self.network = nx.DiGraph()
        self.root = None
        self.node_id = 0

    def node(self, node_id, obj=False):
        if obj:
            return self.network.node[node_id]['obj']
        else:
            return self.network.node[node_id]

    def has_node(self, node_id):
        return (node_id in self.network)

    def node_busy(self, node_id):
        obj = self.network.node[node_id]['obj']
        return obj.busy

    ## Network construction methods.
    ##

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

    def set_root(self, node_id):
        self.root = node_id

    def build(self, node, cores):

        if node is None:
            return

        assert(utils.is_namedtuple(node))

        node_type = type(node).__name__

        ## Traverse in depth first.
        #
        if node_type == 'Net':
            for name, decl in node.decls.items():
                self.build(decl, cores)

        ## Adding net constituents.
        #
        if node_type == 'Net':

            # Add constituents of the net.
            vertices = self.build_net(node.wiring, cores)

            # Allocate net object.
            net = components.Net(node.name, node.inputs, node.outputs)

            # Merge identially named channels.
            copiers = self.flatten_network(vertices)
            vertices += copiers

            ## Mount ports from boxes to net.
            #
            gp = self.get_global_ports(vertices)

            # Inputs.
            for i, name in enumerate(node.inputs):
                if name not in gp['in']:
                    raise ValueError('There is no port named `{}\''
                                     'in the net.'.format(name))
                ports = gp['in'][name]
                assert(len(ports) == 1)
                net.inputs[i] = ports[0][1]

            # Outputs.
            for i, name in enumerate(node.outputs):
                if name not in gp['out']:
                    raise ValueError('There is no port named `{}\''
                                     'in the net.'.format(name))
                ports = gp['out'][name]
                assert(len(ports) == 1)
                net.outputs[i] = ports[0][1]

            self.add_net(net, vertices)

        elif node_type == 'Morphism':
            # Handle morph declaration
            # Add morphism net
            pass

        elif node_type == 'Synchroniser':

            inputs = [c[0] for c in node.obj[3]['in']]
            outputs = [c[0] for c in node.obj[3]['out']]

            sync = components.Syncroniser(node.name, inputs, outputs,
                                          *node.obj[:3])
            self.add_vertex(sync)

    def build_net(self, ast, cores):

        vertices = []

        # Wiring AST: postorder traversal
        ids = nx.dfs_postorder_nodes(ast, ast.graph['root'])
        stack = []

        for nid in ids:
            ast_node = ast.node[nid]

            if ast_node['type'] == 'node':

                # NOTE: only expressions with box names are supported here!!!
                # TODO: support network names in wiring expressions.

                if ast_node['value'] not in cores:
                    raise ValueError('Wrong box name.')

                box_core = cores[ast_node['value']]

                # Box properties and constructor.
                box = utils.box(box_core.__doc__)

                # Generate names of ports.
                inputs = [(ast_node['inputs'].get(i, '_{}'.format(i)))
                          for i in range(box.n_inputs)]
                outputs = [(ast_node['outputs'].get(i, '_{}'.format(i)))
                           for i in range(box.n_outputs)]

                # Create vertex object and insert to network.
                vertex = box.box(ast_node['value'], inputs, outputs, box_core)
                vertex_id = self.add_vertex(vertex)

                stack.append([vertex_id])
                vertices.append(vertex_id)

            elif ast_node['type'] == 'operator':
                rhs = stack.pop()
                lhs = stack.pop()
                operator = ast_node['value']

                # Merge identially named channels of both operands.
                copiers = self.flatten_network(lhs)
                vertices += copiers

                copiers = self.flatten_network(rhs)
                vertices += copiers

                # Apply wiring to operands.
                self.add_connection(operator, lhs, rhs)

                stack.append(lhs + rhs)

        return vertices

    def add_connection(self, operator, lhs, rhs):

        lhs_outputs = self.get_global_ports(lhs)['out']
        rhs_inputs = self.get_global_ports(rhs)['in']

        if operator == '||':
            # Parallel connection: wiring is not required.
            pass

        elif operator == '..':
            # Serial connection: all outputs of the first operand are wired to
            # identically named inputs of the second operand if they exist.

            # Compute identical names.
            common_names = lhs_outputs.keys() & rhs_inputs.keys()

            for name in common_names:
                # Channels with the same names must be already merged.
                assert(len(lhs_outputs[name]) == 1
                       and len(rhs_inputs[name]) == 1)

                # Make `physical' connection between ports.
                self.add_wire(lhs_outputs[name][0], rhs_inputs[name][0])

        else:
            raise ValueError('Wrong wiring operator.')

    def add_wire(self, pa, pb):
        src_vertex, src_port = pa
        dst_vertex, dst_port = pb

        src_port['to'] = dst_port['queue']
        src_port['node_id'] = dst_vertex
        dst_port['node_id'] = src_vertex

    def get_global_ports(self, vertices):

        global_ports = {'in': {}, 'out': {}}

        for vertex_id in vertices:
            vertex = self.node(vertex_id)['obj']

            for p in vertex.inputs:
                if p['node_id'] is None:
                    if p['name'] in global_ports['in']:
                        global_ports['in'][p['name']].append((vertex_id, p))
                    else:
                        global_ports['in'][p['name']] = [(vertex_id, p)]

            for p in vertex.outputs:
                if p['node_id'] is None:
                    if p['name'] in global_ports['out']:
                        global_ports['out'][p['name']].append((vertex_id, p))
                    else:
                        global_ports['out'][p['name']] = [(vertex_id, p)]

        return global_ports

    def flatten_network(self, vertices):

        copiers = []

        gp = self.get_global_ports(vertices)

        # Merge input ports.
        for name, ports in gp['in'].items():
            np = len(ports)
            if np > 1:
                copier_name = '{}_1_to_{}'.format(name, np)
                copier = components.Copier(copier_name, [name], [name]*np)
                copier_id = self.add_vertex(copier)
                copiers.append(copier_id)

                for i, port in enumerate(ports):
                    self.add_wire((copier_id, copier.outputs[i]), port)

        # Merge output ports.
        for name, ports in gp['out'].items():
            np = len(ports)
            if np > 1:
                copier_name = '{}_{}_to_1'.format(name, np)
                copier = components.Copier(copier_name, [name]*np, [name])
                copier_id = self.add_vertex(copier)
                copiers.append(copier_id)

                for i, port in enumerate(ports):
                    self.add_wire(port, (copier_id, copier.inputs[i]))

        return copiers


def dump(network, output_file=None):
    import dill
    import marshal

    # Dump core functions throughout the network to allow the Network
    # object to be serialized.
    for n in network.network.nodes():
        obj = network.node(n)['obj']
        if hasattr(obj, 'core') and obj.core is not None:
            name = obj.core.__name__
            obj.core = (name, marshal.dumps(obj.core.__code__))

    if output_file is None:
        return dill.dumps(network)
    else:
        dill.dump(network, open(output_file, 'wb'))


def load(obj=None, input_file=None):
    import dill
    import marshal
    import types

    if obj is not None:
        network = dill.loads(obj)
    elif input_file is not None:
        network = dill.load(open(input_file, 'rb'))
    else:
        raise ValueError('Either object or input file must be specified.')

    # Deserialize functions' code.
    for n in network.network.nodes():
        obj = network.node(n)['obj']
        if hasattr(obj, 'core') and obj.core is not None:
            code = marshal.loads(obj.core[1])
            obj.core = types.FunctionType(code, globals(), obj.core[0])

    return network
