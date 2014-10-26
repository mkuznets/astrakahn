#!/usr/bin/env python3

import os
import sys
import sync_lexer as lex
import sync_parser as parse
import sync_ir


def build(src_file, args=[]):

    if not (os.path.isfile(src_file) and os.access(src_file, os.R_OK)):
        raise ValueError('File either does not exist or cannot be read.')

    sync_file = open(src_file, 'r')
    sync_code = sync_file.read()

    # Parse source code.
    lexer = lex.build()


    ####################### Code preprocessing ################################

    lexer.input(sync_code)
    sync_code_processed = ''

    stack = ['LBRACKET', 'ID', 'SYNCH']
    macros_done = False
    macro_names = []
    macro_subst = {}

    while True:
        tok = lexer.token()
        if not tok:
            break

        if stack and stack[-1] == tok.type:
            stack.pop()

        if not macros_done and not stack and args:
            if tok.type == 'LPAREN' or tok.type == 'RBRACKET':
                macros_done = True

                if len(args) != len(macro_names):
                    print('Number of arguments does not correspond to the '
                          'number of macros.')
                    quit()

                macro_subst = {n: str(args[i])
                               for i, n in enumerate(macro_names)}

            elif tok.type == 'COMMA':
                pass

            elif tok.type == 'ID':
                macro_names.append(tok.value)

        if macro_subst and tok.type == 'ID' and tok.value in macro_subst:
            token = macro_subst[tok.value]
        else:
            token = str(tok.value)

        sync_code_processed += token + ' '

    ###########################################################################

    lexer = lex.build()
    parser = parse.build('sync')
    ast = parser.parse(sync_code_processed, lexer=lexer)

    return ast

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Provide source file!')
        quit()

    ast = build(sys.argv[1])
    ast.show(attrnames=True, nodenames=True)
