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

    net_ast = parser.parse(code, lexer=lexer)

    return net_ast

