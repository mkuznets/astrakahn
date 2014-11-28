#!/usr/bin/env python3

from . import lexer as net_lexer
from . import parser as net_parser
from . import ast


class NetWiring(ast.NodeVisitor):

    def __init__(self):
        self.exprs = []

    def visit_Net(self, node, children):
        self.exprs += [children['wiring']]

    def visit_BinaryOp(self, node, children):
        return (node.op, children['left'], children['right'])

    def visit_UnaryOp(self, node, children):
        return (node.op, children['operand'])

    def visit_Vertex(self, node, children):
        return node.name

    def generic_visit(self, node, _):
        pass


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

