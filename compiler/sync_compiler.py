#!/usr/bin/env python3

import os
import sys
import sync_lexer as lex
import sync_parser as parse
import sync_ir


class MacroLexer:

    def __init__(self, lexer, macros={}):
        self.lexer = lexer
        self.macros = macros

    def token(self):
        t = self.lexer.token()
        if t is not None \
                and self.macros \
                and t.type == 'ID' and t.value in self.macros:
            t.value = self.macros[t.value]
        return t

    def input(self, code):
        self.lexer.input(code)


def build(src_file, macros={}):

    if not (os.path.isfile(src_file) and os.access(src_file, os.R_OK)):
        raise ValueError('File either does not exist or cannot be read.')

    sync_file = open(src_file, 'r')
    sync_code = sync_file.read()

    lexer = MacroLexer(lex.build(), macros)

    parser = parse.build('sync')
    ast = parser.parse(sync_code, lexer=lexer)

    return ast

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Provide source file!')
        quit()

    ast = build(sys.argv[1])
    ast.show(attrnames=True, nodenames=True)
