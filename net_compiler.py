#!/usr/bin/env python3

import imp
import inspect

import os
import sys

import compiler.net as net

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

    ast = net.parse(src_code)

    #ast.show(attrnames=True, nodenames=True)

    #net.dump(network, 'tests/a.out')
