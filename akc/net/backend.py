#!/usr/bin/env python3

import components
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

        # A declaration with the name corresponding to some box overrides the
        # box.
        non_redefined_cores = {k: v for k, v in self.cores.items() if k not in scope}

        # Add core entries.
        scope.update(non_redefined_cores)

        return scope

    #--------------------------------------------------------------------------

    def visit_SynchTab(self, node, _):
        'final'
        inputs = [p.name.value for p in node.sync.ast.inputs.ports]
        outputs = [p.name.value for p in node.sync.ast.outputs.ports]
        return ('synchtab', node.sync.name, node, inputs, outputs)

    def visit_Synchroniser(self, node, _):
        inputs = [p.name.value for p in node.ast.inputs.ports]
        outputs = [p.name.value for p in node.ast.outputs.ports]
        'final'
        return ('sync', node.name, node, inputs, outputs)

    def visit_Morphism(self, node, _):
        'final'
        return ('morph', node.map, node, ['_1'], ['_1'])

    def visit_Net(self, node, _):
        'final'
        inputs = self.traverse(node.inputs)
        outputs = self.traverse(node.outputs)
        return ('net', node.name, node, inputs, outputs)

    def visit_DeclList(self, node, children):
        return children['decls']

    #--------------------------------------------------------------------------

    def visit_Vertex(self, node, children):
        scope = self.scope()
        obj = None

        if node.name in scope:
            decl = scope[node.name]

            # Port names are computed in compile_box()
            if decl[0] == 'core':
                obj = self.compile_box(decl[1], node)

            elif decl[0] == 'morph':

                boxes = (decl[2].split, decl[2].map, decl[2].join)

                for name in boxes:
                    if name not in self.cores:
                        raise ValueError('Mosphism: box `%s\' not found' % (name))

                split, map, join = (self.cores[n][1] for n in boxes)

                # Transductor
                v = ast.Vertex(node.inputs, node.outputs, decl[2].map, None)
                transductor = self.compile_box(map, v)

                # Inductor
                v = ast.Vertex([], [], decl[2].split, None)
                inductor = self.compile_box(split, v)

                # Reductor
                v = ast.Vertex([], [], decl[2].join, None)
                reductor = self.compile_box(join, v)

                # Prepare port names.
                inputs = [transductor.inputs[0].name]
                inputs.append('_%s' % inputs[0])
                #
                m = transductor.outputs[0].name
                outputs = [m, '_%s' % m]
                outputs += ['%s' % p.name for pid, p
                            in sorted(transductor.outputs.items()) if pid > 0]

                # Morphism
                obj = components.Morphism(decl[2].map, inputs, outputs,
                               inductor, transductor, reductor)

            # Port names are computed right here.
            else:
                n_in, n_out = len(decl[3]), len(decl[4])

                # Rename ports.
                inputs = self._rename_ports(n_in, node.inputs, decl[3])
                outputs = self._rename_ports(n_out, node.outputs, decl[4])

                if decl[0] == 'net':
                    obj = self.compile_net(decl[2], inputs, outputs)

                elif decl[0] == 'sync':
                    obj = self.compile_sync(decl[2], inputs, outputs)

                elif decl[0] == 'synchtab':
                    labels = decl[2].labels
                    obj = self.compile_synchtab(node.name, decl[2].sync.ast, labels)

                else:
                    raise ValueError('Node %s is of unknown type: `%s\''
                                     % (node.name, type))

        elif node.name == '~':
            if type(node.inputs) is not list or type(node.outputs) is not list:
                raise RuntimeError('Merger requires a list of ports, not'
                                   'key-value pairs.')

            obj = self.compile_merger(node.inputs, node.outputs)

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
        inputs = self.traverse(ast.inputs)
        outputs = self.traverse(ast.outputs)

        return self.compile_net(ast, inputs, outputs)

    def compile_sync(self, sync, inputs, outputs):
        sb = SyncBuilder(inputs, outputs)
        obj = sb.traverse(sync.ast)
        return obj

    def compile_synchtab(self, name, sync_ast, labels):
        # Get port names
        inputs = [p.name.value for p in sync_ast.inputs.ports]
        outputs = [p.name.value for p in sync_ast.outputs.ports]

        obj = components.SynchTable(name, inputs, outputs, sync_ast, labels)
        return obj

    def compile_net(self, net, inputs, outputs):
        assert(type(net) == ast.Net)

        decls = self.traverse(net.decls)
        scope = {d[1]: d for d in decls}

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

            inputs = self._rename_ports(n_in, vertex.inputs)
            outputs = self._rename_ports(n_out, vertex.outputs)

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

    def _rename_ports(self, n, rename, defaults=None):

        if not defaults:
            defaults = ['_%s' % (i+1) for i in range(n)]

        if type(rename) is list:
            rename_map = dict(zip(defaults, rename))
        elif type(rename) is dict:
            rename_map = rename
        else:
            raise ValueError('Wrong ports in renaming bracket.')

        return [(rename_map.get(name, name)) for name in defaults]

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
