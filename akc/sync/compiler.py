#!/usr/bin/env python3

import os
import sys
import imp
import re

from . import lexer as sync_lexer
from . import parser as sync_parser


def macro_subst(code, macros):
    code_final = ''

    lexer = sync_lexer.build()
    lexer.input(code)

    while True:
        t = lexer.token()

        if t is None:
            break

        if t.type == 'ID' and t.value in macros:
            code_final += str(macros[t.value])
        else:
            code_final += str(t.value)

    return code_final


def parse(code, macros={}):
    global sync_lexer

    #if macros:
    #    code = macro_subst(code, macros)

    code_lines = code.split('\n')

    configs = {}

    # Read parameters from the header.
    for i, line in enumerate(code_lines):
        line = line.strip()
        if line.startswith('@'):
            match = re.findall("\@([A-Za-z_][\w_]*)(?:(?:\s*)\=(?:\s*)([\w\d]+))?$", line)
            if not match:
                continue
            else:
                name, value = match[0]

                if type(value) == str and value.isdigit():
                    value = int(value)

                configs[name] = macros.get(name, value)

        elif line.startswith('synch'):
            code = "\n".join(code_lines[i:])

    sync_parser.configs = configs

    for name in configs:
        sync_parser.config_nodes[name] = []

    lexer = sync_lexer.build()
    parser = sync_parser.build()

    sync_ast = parser.parse(code, lexer=lexer)
    sync_ast.configs = sync_parser.config_nodes

    return sync_ast
