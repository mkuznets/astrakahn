#!/usr/bin/env python3

from . import lexer as net_lexer
from . import parser as net_parser
from . import ast

from compiler.sync.backend import SyncBuilder
from compiler.net.backend import NetBuilder


class SyncParser(ast.NodeVisitor):

    def __init__(self, syncs):
        self.syncs = syncs

    def visit_Synchroniser(self, node, children):

        if node.name not in self.syncs:
            raise ValueError('Synchroniser `%s\' not found' % node.name)

        src_code = self.syncs[node.name]

        from compiler.sync import parse as sync_parse
        sync_ast = sync_parse(src_code, node.macros)

        node.ast = sync_ast


def parse(code, syncs=None, output_handler=True):

    lexer = net_lexer.build()
    parser = net_parser.build()

    # Generate net AST.
    net_ast = parser.parse(code)

    if not net_ast:
        raise ValueError('AST was not build due to some error.')

    # Traverse AST and parse synchronisers.
    if syncs:
        SyncParser(syncs).traverse(net_ast)

    # Manually add and connect handler vertex before net output.
    if output_handler:
        wiring = net_ast.wiring
        outputs = [p.value for p in net_ast.outputs.ports]
        #
        v = ast.Vertex(outputs, outputs, '__output__', None)
        net_ast.wiring = ast.BinaryOp('..', wiring, v)

    return net_ast


def compile(code, cores, syncs=None):

    # Generate AST from net source code.
    net_ast = parse(code, syncs)

    # Generate runtime component network from AST.
    net = NetBuilder(cores).compile(net_ast)

    return net
