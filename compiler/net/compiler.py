#!/usr/bin/env python3

from . import lexer as net_lexer
from . import parser as net_parser
from . import ast


class Stars(ast.NodeVisitor):

    def __init__(self):
        pass

    def visit_UnaryOp(self, node, children):
        if node.op == '*':

            print(node.operand)



def parse(code):
    lexer = net_lexer.build()
    parser = net_parser.build()

    net_ast = parser.parse(code)

    wiring = net_ast.wiring
    outputs = {i: p.value for i, p in enumerate(net_ast.outputs.ports)}

    # Add an output handler.
    net_ast.wiring = ast.BinaryOp('..', wiring, ast.Vertex('__output__', None,
                                                            outputs, outputs))

    return net_ast

