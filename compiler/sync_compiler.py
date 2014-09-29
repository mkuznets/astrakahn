#!/usr/bin/env python3

import os
import sync_lexer as lex
import sync_parser as parse
import sync_ir


def build(src_file):

    if not (os.path.isfile(src_file) and os.access(src_file, os.R_OK)):
        raise ValueError('File either does not exist or cannot be read.')

    sync_file = open(src_file, 'r')
    sync_code = sync_file.read()

    # Parse source code.
    lexer = lex.build()
    parser = parse.build()
    parser.parse(sync_code, lexer=lexer)
    sync_ast = parse.ast

    ir = sync_ir.build(sync_ast)

    return ir
