#!/usr/bin/env python3

keywords = ['NET', 'PURE', 'CONNECT', 'END', 'MORPH', 'SYNC', 'TAB']

tokens = keywords + [
    'ID', 'NUMBER', 'SERIAL', 'PARALLEL', 'STAR', 'BACKSLASH', 'COMMA', 'VBAR',
    'LE', 'GE', 'LPAREN', 'RPAREN', 'LBRACKET', 'RBRACKET', 'SLASH', 'EQUAL',
    'LBRACE', 'RBRACE', 'COLON', 'MERGE'
]

# Tokens

# net operators
t_SERIAL        = r'\.\.'
t_PARALLEL      = r'\|\|'
t_STAR          = r'\*'
t_BACKSLASH     = r'\\'

t_COMMA         = r','
t_VBAR          = r'\|'
t_LE            = r'<'
t_GE            = r'>'
t_LPAREN        = r'\('
t_RPAREN        = r'\)'
t_LBRACKET      = r'\['
t_RBRACKET      = r'\]'
t_SLASH         = r'/'
t_EQUAL         = r'='
t_LBRACE        = r'{'
t_RBRACE        = r'}'
t_COLON         = r':'
t_MERGE         = r'~'
t_ignore_COMMENT = r'\#.*'

keywords_map = {k.lower(): k for k in keywords}


def t_ID(t):
    r'[A-Za-z_][\w_]*'
    t.type = keywords_map.get(t.value, 'ID')
    return t


def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

t_ignore = " \t"


def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

###############################################################################

import ply.lex as lex


def build():
    return lex.lex()
