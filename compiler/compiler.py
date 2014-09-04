#!/usr/bin/env python3

import imp
import os
import sys
import inspect
import lexer as lex
import parser as parse

sys.path.insert(0, os.path.dirname(__file__) + '/..')
import network as net


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

    cores = {name: func
             for name, func in inspect.getmembers(src, inspect.isfunction)}
    network = net.Network()

    # Parse source code.
    lexer = lex.build()
    parser = parse.build()
    parser.parse(src_code, lexer=lexer)
    ast = parse.ast

    # Network construction.
    network.build(ast, cores)

    # TODO: Must be done autotomatically after network construction.
    network.set_root(network.node_id - 1)

    net.dump(network, 'tests/a.out')
