#!/usr/bin/env python3

import os
import sys
import compiler.sync as sync


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print('USAGE: {} source'.format(sys.argv[0]))
        quit()

    src_file = sys.argv[1]

    if not (os.path.isfile(src_file) and os.access(src_file, os.R_OK)):
        print('Source file either does not exist or cannot be read.')
        quit()

    src_code = open(src_file, 'r').read()

    ast = sync.parse(src_code)

    ast.show(attrnames=True, nodenames=True)
