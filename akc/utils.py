#!/usr/bin/env python3

import inspect
import os


def is_namedtuple(x):
    t = type(x)
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple):
        return False
    return all(type(n) == str for n in f)


def rprint(obj, offset=0):

    if is_namedtuple(obj):
        print(type(obj).__name__)
        offset += 2

        names = obj._fields
        maxlen = max(map(len, names))

        for n in obj._fields:
            left_border = maxlen + 2
            n_spaces = left_border - len(n)

            print((' ' * offset) + n + ':' + (' ' * n_spaces), end='')
            item = obj.__getattribute__(n)
            rprint(item, left_border + offset + 1)
        print()

    elif type(obj) == list:
        if sum(map(len, (str(i) for i in obj))) < 80:
            print(obj)
            return

        item_offset = offset + 2

        print('[')

        for item in obj:
            print((' ' * item_offset), end='')
            rprint(item, item_offset)

        print((' ' * offset) + ']')

    else:
        print(str(obj))


def print_ast_dot(ast):

    print('digraph AST {')
    # print("\tnode [shape=plaintext];")

    for n in ast.nodes():
        properties = {}

        attrs = ast.node[n]
        if attrs['type'] == 'node':
            properties['shape'] = 'box'

        properties['label'] = attrs['value'].replace("\\", "\\\\")

        if 'inputs' in attrs or 'outputs' in attrs:
            inputs = ', '.join(name for i, name in attrs['inputs'].items())
            outputs = ', '.join(name for i, name in attrs['outputs'].items())
            properties['label'] += "\\nInputs: {}\\n"\
                "Outputs: {}".format(inputs, outputs)

        properties_str = ', '.join('{}="{}"'.format(k, v)
                                   for k, v in properties.items())

        print("\t{} [{}];".format(n, properties_str))

    for e in ast.edges():
        print("\t{} -> {}".format(*e))

    print('}')


def is_box(d):
    return inspect.isfunction(d) and hasattr(d, '__box__')


def is_file_readable(filename):
    return os.path.isfile(filename) and os.access(filename, os.R_OK)
