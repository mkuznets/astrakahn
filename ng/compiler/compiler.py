#!/usr/bin/env python3

import imp
import os
import sys
import inspect
import lexer as lex
import parser as parse
import utils

sys.path.insert(0, os.path.dirname(__file__) + '/..')
import network


net = network.Network()


def build_network(node):
    global net

    if node is None:
        return

    assert(utils.is_namedtuple(node))

    node_type = type(node).__name__

    if node_type == 'Net':
        for d in node.decls:
            build_network(d)

    # Adding net constituents.

    if node_type == 'Morphism':
        # Handle morph declaration
        # Add morphism net
        pass

    elif node_type == 'Net':
        # Handle AST
        ast = node.wiring


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print('USAGE: {} source'.format(sys.argv[0]))
        quit()

    src_file = sys.argv[1]

    if not (os.path.isfile(src_file) and os.access(src_file, os.R_OK)):
        print('Source file either does not exist or cannot be read.')
        quit()

    # Import source code from docstring of source file.
    src_name = os.path.basename(src_file)
    src = imp.load_source(src_name, src_file)
    src_code = src.__doc__

    global_boxes = {name: func for name, func in inspect.getmembers(src, inspect.isfunction)}

    # Parse source code.
    lexer = lex.build()
    parser = parse.build()
    parser.parse(src_code, lexer=lexer)
    ast = parse.ast

