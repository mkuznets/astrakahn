#!/usr/bin/env python3

import sys
import os
import re
import collections

sys.path.insert(0, os.path.dirname(__file__) + '/..')
import network

def is_namedtuple(x):
    t = type(x)
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple):
        return False
    return all(type(n)==str for n in f)


def box(category):
    box_tuple = collections.namedtuple("Box",
                                       "box n_inputs n_outputs ord seg")

    # Type handling
    cat_re = re.compile('([1-9]\d*)(T|I|DO|DU)')
    #cat_re = re.compile('([1-9]\d*)(T|I|DO|DU|MO|MS|MU)')
    parse = cat_re.findall(category.strip())

    if not parse:
        raise ValueError("Wrong box category")

    n1, cat = parse[0]
    ordered = None
    segmentable = None

    n_outputs = int(n1)
    n_inputs = 2 if cat[0] == 'D' else 1

    # Assign box class
    if cat == 'T':
        box_class = network.Transductor

    elif cat == 'I':
        box_class = network.Inductor

    elif cat[0] == 'D':
        box_class = network.DyadicReductor
        ordered = True if cat[1] != 'U' else False
        segmentable = True if cat[1] == 'S' or cat[1] == 'U' else False

    else:
        raise ValueError("Wrong box category")

    return box_tuple(box_class, n_inputs, n_outputs, ordered, segmentable)


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
    #print("\tnode [shape=plaintext];")

    for n in ast.nodes():
        properties = {}

        attrs = ast.node[n]
        if attrs['type'] == 'node':
            properties['shape'] = 'box'

        properties['label'] = attrs['value'].replace("\\", "\\\\")

        if 'inputs' in attrs or 'outputs' in attrs:
            inputs = ', '.join(name for i, name in attrs['inputs'].items())
            outputs = ', '.join(name for i, name in attrs['outputs'].items())
            properties['label'] += "\\nInputs: {}\\nOutputs: {}".format(inputs, outputs)

        properties_str = ', '.join('{}="{}"'.format(k, v) for k, v in properties.items())

        print("\t{} [{}];".format(n, properties_str))

    for e in ast.edges():
        print("\t{} -> {}".format(*e))

    print('}')
