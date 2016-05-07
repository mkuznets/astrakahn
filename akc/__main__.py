#!/usr/bin/env python3

import os
import stat
import inspect
from optparse import OptionParser

from importlib.util import spec_from_file_location, module_from_spec
from collections import defaultdict

from .net.compiler import compile
from .utils import is_box, is_file_readable

import aksync.compiler

__runtime_pkg__ = 'akr'

usage = "usage: %prog [options] file"
opts = OptionParser(usage=usage)

opts.add_option('-o', '--output', type='string', dest='output',
                metavar='OUTPUT', default='a.py')
opts.add_option('-p', '--nproc', type='int', dest='np', metavar='NPROC',
                default=1)
opts.add_option('-d', action='store_true', dest='debug', default=False)

if __name__ == '__main__':

    (options, args) = opts.parse_args()

    if len(args) != 1:
        opts.error('Input file is required')

    src_filename = str(args[0])

    if not is_file_readable(src_filename):
        raise ValueError('Input file does not exist or cannot be read')

    # ----

    module_name = os.path.basename(src_filename).split('.')[0]

    # Box definitions source
    decls_filename = os.path.join(os.path.dirname(src_filename),
                                  module_name + '.py')

    spec = spec_from_file_location(module_name + '.py', decls_filename)
    decls = module_from_spec(spec)
    spec.loader.exec_module(decls)

    # Get decorated box functions.
    box_members = inspect.getmembers(decls, predicate=is_box)
    boxes = {n: f() for n, f in box_members}

    # Synchronisers source
    syncs_filename = os.path.join(os.path.dirname(src_filename),
                                  module_name + '.sync')

    with open(syncs_filename, 'r') as src_file:
        syncs = {ast.name.value: ast
                 for ast in aksync.compiler.compile_to_ast(src_file.read())}

    # ----

    with open(src_filename, 'r') as src_file:
        graph, used_boxes, used_syncs = compile(src_file.read(), boxes, syncs)

    graph.convert_to_ir()

    if options.debug:
        graph.pprint()

    output = "#!/usr/bin/env python3\n\n"
    output += "import %s\n\n" % __runtime_pkg__

    if used_syncs:
        output += aksync.compiler.preamble()

    boxes = {box.func.__name__: box for box in used_boxes}

    # Box functions.
    for box in boxes.values():
        func_lines = inspect.getsourcelines(box.func)[0]

        if hasattr(box.func, 'ordered'):
            decorator = "@%s.%s(%s)\n" % (__runtime_pkg__, box.func.cat,
                                          box.func.ordered)

        else:
            decorator = "@%s.%s\n" % (__runtime_pkg__, box.func.cat)

        if func_lines[0].startswith('@'):
            func_lines[0] = decorator
        else:
            func_lines.insert(0, decorator)

        output += "".join(func_lines)
        output += "\n"

    # Output handler.
    handler = inspect.getsourcelines(decls.__output__)[0]
    output += "@%s.output\n" % __runtime_pkg__
    output += ''.join(handler)
    output += "\n"

    # Synchronisers
    for sync in used_syncs:
        ast = syncs[sync.name]
        output += aksync.compiler.compile_sync(ast)

    # Reverse exit mapping
    exit_bbs = defaultdict(list)
    for channel, bb in graph.exit.items():
        exit_bbs[bb].append(channel)

    # Add exit nodes.
    for bb, channels in exit_bbs.items():
        # Create separate output vertex for each output as multi-input vertices
        # are not currently supported
        for ch in channels:
            exit_node = '%s_exit_%s' % (bb, ch)

            graph.add_node(exit_node,
                           stmts=[('__output__', (ch,), ())],
                           exit=True)
            graph.add_edge(bb, exit_node, {'chn': {ch}})

    # Control flow graph.
    output += "nodes = [\n"
    for n in graph.nodes(data=True):
        stmts = ', '.join('(%s, %s, %s)' % (f, ins, outs)
                          for f, ins, outs in n[1]['stmts'])

        output += "    ('%s', {'stmts': [%s]}),\n" % (n[0], stmts)
    output += "]\n\n"

    output += "edges = [\n"
    for n in graph.edges(data=True):
        output += "    %s,\n" % str(n)
    output += "]\n\n"

    output += "cfg = %s.DiGraph()\n" % __runtime_pkg__
    output += "cfg.add_nodes_from(nodes)\n"
    output += "cfg.add_edges_from(edges)\n"
    output += "cfg.entry = %s\n" % repr(graph.entry)
    output += "cfg.exit = %s\n" % repr(graph.exit)
    output += "\n"

    # Input.
    output += "__input__ = %s\n\n" % repr(decls.__input__)

    # Runners.
    output += "runner = %s.Runner(cfg, __input__)\n" % __runtime_pkg__
    output += "runner.run()\n"

    with open(options.output, 'w') as f:
        f.write(output)

        mode = os.fstat(f.fileno()).st_mode
        mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.fchmod(f.fileno(), stat.S_IMODE(mode))
