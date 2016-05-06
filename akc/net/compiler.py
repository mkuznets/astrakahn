#!/usr/bin/env python3

from . import lexer as net_lexer
from . import parser as net_parser
from . import ast

from akc.net.backend import NetBuilder


def parse(code):

    lexer = net_lexer.build()
    parser = net_parser.build()

    # Generate net AST.
    net_ast = parser.parse(code)

    if not net_ast:
        raise ValueError('AST was not build due to some error.')

    return net_ast


def compile(code, boxes, syncs):

    # Generate AST from net source code.
    net_ast = parse(code)

    # Generate runtime component network from AST.
    net, used_boxes, used_syncs = NetBuilder(boxes, syncs).compile(net_ast)

    return net, used_boxes, used_syncs
