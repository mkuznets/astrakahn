#!/usr/bin/env python3

import components
from network import Network
from compiler.sync import parse as sync_parse
from compiler.sync.backend import SyncBuilder
from . import ast
import visitors

import re
import os.path

class NetBuilder(ast.NodeVisitor):

    def __init__(self, cores):
        self.cores = cores

        self.scope_stack = []
        self.net_stack = []

        self.network = None

    #--------------------------------------------------------------------------

    def generic_visit(self, node, children):
        print('Generic', node)

    def get_net(self):
        assert(self.net_stack)
        return self.net_stack[-1]

    def scope(self):
        # Stack of scopes mustn't be empty
        assert(self.scope_stack)

        # Copy the scope at the top of the stack
        scope = self.scope_stack[-1].copy()

        # Add core entries.
        scope.update(self.cores)

        return scope

    #--------------------------------------------------------------------------

    def visit_Synchroniser(self, node, children):
        return ('sync', node, node.name)

    def visit_Morphism(self, node, children):
        'final'
        return ('morph', node, node.map)

    def visit_Net(self, node, children):
        'final'
        return ('net', node, node.name)

    def visit_DeclList(self, node, children):
        return children['decls']

    #--------------------------------------------------------------------------

    def visit_Vertex(self, node, children):
        scope = self.scope()
        obj = None

        if node.name in scope:
            type, decl, *_ = scope[node.name]

            if type == 'net':
                obj = self.compile_net(decl, node)

            elif type == 'morph':
                raise NotImplementedError('¯\_(ツ)_/¯')

            elif type == 'sync':
                obj = self.compile_sync(decl.ast)

            elif type == 'core':
                obj = self.compile_box(decl, node)

            else:
                raise ValueError('Node %s is of unknown type: `%s\''
                                 % (node.name, type))

        elif node.name == '~':
            obj = self.compile_merger(list(node.inputs.values()),
                                      list(node.outputs.values()))

        else:
            raise ValueError('Node %s is undefined.' % node.name)

        assert(obj is not None)

        net = self.get_net()
        nid = net.add_node(obj)

        return set((nid,))

    def visit_BinaryOp(self, node, children):

        left, right = children['left'], children['right']

        net = self.get_net()

        if node.op == '||':
            # Parallel connection: no wiring performs.
            pass

        elif node.op == '..':
            # Serial connection: all outputs of the first operand are wired to
            # identically named inputs of the second operand if they exist.

            left = self._flatten(left)
            right = self._flatten(right)

            _, left_outputs = self._free_ports(left)
            right_inputs, _ = self._free_ports(right)

            # Compute identical port names.
            common_ports = left_outputs.keys() & right_inputs.keys()

            for name in common_ports:
                # Channels with the same names must be already merged.
                assert(len(left_outputs[name]) == 1
                       and len(right_inputs[name]) == 1)

                # Make `physical' connection between ports.
                net.add_wire(left_outputs[name][0], right_inputs[name][0])

        else:
            raise ValueError('Wrong wiring operator.')

        operands = left | right
        return operands

    def visit_UnaryOp(self, node, children):

        operand = self._flatten(children['operand'])
        inputs, outputs = self._free_ports(operand)

        net = self.get_net()

        if node.op == '*':
            pass
            #if len(operand) != 1:
            #    raise ValueError('*-operator can be applied to net only.')

            #net = operand.pop()

            #if type(net) is not components.Net:
            #    raise ValueError('*-operator can be applied to net only.')

            #if len(inputs) != 1 or len(outputs) != 3:
            #    raise ValueError('Stage layout: wrong number of inpus or outputs')

            #stage_port = list(inputs)[0]

            #if (stage_port not in outputs) or ('__output__' not in outputs):
            #    raise ValueError('Stage layout: wrong channel naming.')

            #mrgr = components.Merger('__star_output__', ['__exit__'], [stage_port])
            #mrgr.id = self._get_node_id()

            #star_net = components.StarNet('__' + net.name + '_fps__',
            #                              [stage_port], [stage_port],
            #                              [net, mrgr])
            #star_net.id = self._get_node_id()

            #star_net.stages.append(net)
            #star_net.stage_port = stage_port
            #star_net.merger = mrgr

            #star_net.wire_stages()

            #operand = set((star_net,))

        elif node.op == '\\':

            # Compute identical port names.
            common_ports = inputs.keys() & outputs.keys()

            for name in common_ports:
                # Channels with the same names must be already merged.
                assert(len(inputs[name]) == 1 and len(outputs[name]) == 1)

                # Make `physical' connection between ports.
                net.add_wire(outputs[name][0], inputs[name][0])

        return operand

    #--------------------------------------------------------------------------

    def visit_PortList(self, node, children):
        return children['ports']

    def visit_ID(self, node, _):
        return node.value

    #--------------------------------------------------------------------------

    def compile(self, ast):
        obj = self.compile_net(ast)
        network = Network(obj)

        return network

    def compile_sync(self, sync_ast):
        sb = SyncBuilder()
        obj = sb.traverse(sync_ast)
        return obj

    def compile_net(self, net, vertex=None):
        assert(type(net) == ast.Net)

        decls = self.traverse(net.decls)

        scope = {}
        for d in decls:
            scope[d[2]] = d


        inputs = self.traverse(net.inputs)
        outputs = self.traverse(net.outputs)

        obj = components.Net(net.name, inputs, outputs)

        # Push current scope to stack
        self.scope_stack.append(scope)

        self.net_stack.append(obj)

        nodes = self.traverse(net.wiring)
        nodes = self._flatten(nodes)

        cv = visitors.CoreVisitor()
        cv.traverse(obj)

        obj.id = 0
        obj.cores = cv.cores

        obj.ast = net

        nodes_inputs, nodes_outputs = self._free_ports(nodes)

        ## Mount inputs.
        for i, p in obj.inputs.items():
            if p.name not in nodes_inputs:
                raise ValueError('There is no input port named `%s\' '
                                 'in the net.' % p.name)
            endpoint = nodes_inputs[p.name][0]
            obj.mount_input_port(i, endpoint)

        ## Mount outputs.
        for i, p in obj.outputs.items():
            if p.name not in nodes_outputs:
                raise ValueError('There is no input port named `%s\' '
                                 'in the net.' % p.name)
            endpoint = nodes_outputs[p.name][0]
            obj.mount_output_port(i, endpoint)

        self.scope_stack.pop()
        self.net_stack.pop()

        return obj

    def compile_box(self, box, vertex):

        # Match box specification from docstring.
        spec = str(box.__doc__).strip()
        m = re.match('^([1-9]\d*)(T|T\*|I|DO|DU|MO|MU|MS|H)$', spec)

        if m:
            n_out, cat = m.groups()
            n_out = int(n_out)

            if cat[0] == 'H':
                n_in = len(vertex.inputs)
                n_out = len(vertex.outputs)
            else:
                n_in = 2 if cat[0] == 'D' else 1

            inputs = self._gen_ports(n_in, vertex.inputs)
            outputs = self._gen_ports(n_out, vertex.outputs)

            if cat == 'T':
                obj = components.Transductor(vertex.name, inputs, outputs, box)

            elif cat == 'T*':
                obj = components.PTransductor(vertex.name, inputs, outputs, box)


            elif cat == 'I':
                obj = components.Inductor(vertex.name, inputs, outputs, box)

            elif cat[0] == 'D':
                ordered = True if cat[1] != 'U' else False
                segmentable = False

                obj = components.DyadicReductor(vertex.name, inputs, outputs, box,
                                     ordered, segmentable)

            elif cat[0] == 'M':
                ordered = True if cat[1] != 'U' else False
                segmentable = True if cat[1] == 'S' or cat[1] == 'U' else False

                obj = components.MonadicReductor(vertex.name, inputs, outputs,
                                                 box, ordered, segmentable)

            elif cat == 'H':
                obj = components.Executor(vertex.name, inputs, outputs, box)

            else:
                raise ValueError('Wrong box category: %s:%s' % (vertex.name,
                                                                cat))
            obj.ast = vertex
            return obj

        else:
            raise ValueError('Wrong box specification: %s:%s' % (vertex.name,
                                                                 spec))
    def compile_ptrans(self):
        pass

    def compile_merger(self, inputs, outputs):

        if len(inputs) == 1:
            merger_name = '%s_1_to_%s' % (inputs[0], '-'.join(set(outputs)))
        elif len(outputs) == 1:
            merger_name = '%s_to_%s_1' % ('-'.join(set(inputs)), outputs[0])
        else:
            merger_name = '%s_to_%s' % ('-'.join(set(inputs)),
                                        '-'.join(set(outputs)))

        obj = components.Merger(merger_name, inputs, outputs)
        return obj

    #--------------------------------------------------------------------------

    def _gen_ports(self, n, rename):
        return [(rename.get(i, '_%s' % (i+1))) for i in range(n)]

    def _free_ports(self, nodes):
        inputs = {}
        outputs = {}

        net = self.get_net()

        for nid in nodes:
            fp = net.get_node(nid).free_ports()

            # Collect free inputs
            for name, ports in fp[0].items():
                inputs[name] = inputs.get(name, []) + ports

            # Collect free outputs
            for name, ports in fp[1].items():
                outputs[name] = outputs.get(name, []) + ports

        return (inputs, outputs)

    def _flatten(self, nodes):

        mergers = set()
        net = self.get_net()

        inputs, outputs = self._free_ports(nodes)

        # Merger for inputs
        for name, ports in inputs.items():
            np = len(ports)

            if np > 1:
                obj = self.compile_merger([name], [name]*np)
                merger_id = net.add_node(obj)
                mergers.add(merger_id)

                for i, port in enumerate(ports):
                    net.add_wire((merger_id, i), port)

        # Merger for outputs
        for name, ports in outputs.items():
            np = len(ports)

            if np > 1:
                obj = self.compile_merger([name]*np, [name])
                merger_id = net.add_node(obj)
                mergers.add(merger_id)

                for i, port in enumerate(ports):
                    net.add_wire(port, (merger_id, i))

        return nodes | mergers

    #--------------------------------------------------------------------------
