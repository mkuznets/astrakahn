#!/usr/bin/env python3

import os
import sys
import inspect
from optparse import OptionParser

from importlib.util import spec_from_file_location, module_from_spec

from akc.net.compiler import compile

usage = "usage: %prog [options] file"
opts = OptionParser(usage=usage)

opts.add_option('-m', '--module', type='string', dest='module', metavar='NAME')
opts.add_option('-n', '--nproc', type='int', dest='np', metavar='NUM', default=1)

if __name__ == '__main__':

    (options, args) = opts.parse_args()

    if len(args) != 1:
        opts.error('Input file is required')

    src_filename = args[0]

    if not (os.path.isfile(src_filename) or os.access(src_filename, os.R_OK)):
        raise ValueError('Input file does not exist or cannot be read')

    # Same filename with .py extension in the same dir
    module_name = os.path.basename(src_filename).split('.')[0] + '.py'
    decls_filename = os.path.join(os.path.dirname(src_filename),
                                  module_name)

    spec = spec_from_file_location(module_name, decls_filename)
    decls = module_from_spec(spec)
    spec.loader.exec_module(decls)

    cores = {n[2:]: getattr(decls, n) for n in dir(decls) if n.startswith('c_')}
    syncs = {n[2:]: getattr(decls, n) for n in dir(decls) if n.startswith('s_')}

    with open(src_filename, 'r') as src_file:
        src_text = src_file.read()

        compile(src_text, cores, syncs)
