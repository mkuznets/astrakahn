#!/usr/bin/env python3

import os
import sys
import imp

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

    if macros:
        code = macro_subst(code, macros)

    sync_lexer.disable_ws()

    lexer = sync_lexer.build()
    parser = sync_parser.build()

    sync_ast = parser.parse(code, lexer=lexer)

    sync_lexer.enable_ws()

    return sync_ast
