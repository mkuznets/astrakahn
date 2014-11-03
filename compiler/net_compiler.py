#!/usr/bin/env python3

import imp
import os
import sys
import inspect
import net_lexer as lex
import net_parser as parse
import sync_compiler

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
    src_dir = os.path.dirname(src_file)
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

    # Look for declared synchronisers and compile them.
    for name, decl in ast.decls.items():
        if type(decl).__name__ == 'Synchroniser':
            sync_obj = sync_compiler.build(src_dir + '/' + decl.name + '.sync', decl.macros)
            ast.decls[name] = parse.Synchroniser(decl[0], decl[1], sync_obj)

    # Network construction.
    network.build(ast, cores)

    # TODO: Must be done automatically after network construction.
    network.set_root(network.node_id - 1)

    for node_id in network.network.nodes():
        node = network.node(node_id, True)
        print(node.id, node, node.name)
        print(node.inputs)
        print(node.outputs)
        print()

    print(network.network.edges())

    net.dump(network, 'tests/a.out')
