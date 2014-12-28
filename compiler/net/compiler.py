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

    def __init__(self, path):
        self.path = path

    def visit_Synchroniser(self, node, children):

        # Path of sync source: if it is not provided from net, use
        #path of net source file.
        if not node.path:
            sync_path = self.path
            sync_file = os.path.join(sync_path, '%s.sync' % node.name)
        else:
            if node.path[0] == '/':
                sync_path = node.path
            else:
                sync_path = os.path.join(self.path, node.path)

            sync_file = sync_path

        if not (os.path.isfile(sync_file)
                and os.access(sync_file, os.R_OK)):
            raise ValueError('File for sync `%s\' is not found or '
                             'cannot be read.' % node.name)

        with open(sync_file, 'r') as f:
            src_code = f.read()

        from compiler.sync import parse as sync_parse
        sync_ast = sync_parse(src_code, node.macros)

        node.ast = sync_ast


def parse(code, path):
    lexer = net_lexer.build()
    parser = net_parser.build()

    net_ast = parser.parse(code)

    wiring = net_ast.wiring
    outputs = {i: p.value for i, p in enumerate(net_ast.outputs.ports)}

    csync = CompileSync(path)
    csync.traverse(net_ast)

    # Add an output handler.
    net_ast.wiring = ast.BinaryOp('..', wiring, ast.Vertex('__output__', None,
                                                            outputs, outputs))

    return net_ast

