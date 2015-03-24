#!/usr/bin/env python3

from . import lexer as net_lexer
from . import parser as net_parser
from . import ast
from compiler.sync.backend import SyncBuilder

import re
import os.path

class Stars(ast.NodeVisitor):

    def __init__(self):
        pass

    def visit_UnaryOp(self, node, children):
        if node.op == '*':

            print(node.operand)

class CompileSync(ast.NodeVisitor):

    def __init__(self, syncs):
        self.syncs = syncs

    def visit_Synchroniser(self, node, children):


        if node.name not in self.syncs:
            raise ValueError('Synchroniser `%s\' not found' % node.name)

        src_code = self.syncs[node.name]

        from compiler.sync import parse as sync_parse
        sync_ast = sync_parse(src_code, node.macros)

        node.ast = sync_ast


def parse(code, syncs):
    lexer = net_lexer.build()
    parser = net_parser.build()

    net_ast = parser.parse(code)

    wiring = net_ast.wiring
    outputs = [p.value for p in net_ast.outputs.ports]

    csync = CompileSync(syncs)
    csync.traverse(net_ast)

    # Add an output handler.
    net_ast.wiring = ast.BinaryOp('..', wiring, ast.Vertex('__output__', None,
                                                            outputs, outputs))

    return net_ast

