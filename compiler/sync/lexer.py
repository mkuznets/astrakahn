#!/usr/bin/env python3

keywords = ['SYNCH', 'STORE', 'STATE', 'INT', 'ENUM', 'ON', 'ELSEON', 'ELSE',
            'SET', 'SEND', 'GOTO', 'THIS', 'NIL']

tokens = keywords + [
    'ID', 'NUMBER', 'LBRACE', 'RBRACE', 'LPAREN', 'RPAREN', 'LBRACKET',
    'RBRACKET', 'COLON', 'PLUS', 'MINUS', 'MULT', 'DIVIDE', 'MOD', 'SHL',
    'SHR', 'LE', 'GE', 'GEQ', 'LEQ', 'EQ', 'NEQ', 'NOT', 'BAND', 'BOR', 'BXOR',
    'LAND', 'LOR', 'COMMA', 'DOT', 'AT', 'QM', 'TO', 'ASSIGN', 'SCOLON',
    'APOSTR'
]

# Tokens

t_LBRACE        = r'{'
t_RBRACE        = r'}'
t_LPAREN        = r'\('
t_RPAREN        = r'\)'
t_LBRACKET      = r'\['
t_RBRACKET      = r'\]'
t_COLON         = r':'
t_PLUS          = r'\+'
t_MINUS         = r'-'
t_MULT          = r'\*'
t_DIVIDE        = r'/'
t_MOD           = r'%'
t_SHL           = r'<<'
t_SHR           = r'>>'
t_LE            = r'<'
t_GE            = r'>'
t_GEQ           = r'>='
t_LEQ           = r'<='
t_EQ            = r'=='
t_NEQ           = r'!='
t_NOT           = r'!'
t_BAND          = r'&'
t_BOR           = r'\|'
t_BXOR          = r'\^'
t_LAND          = r'&&'
t_LOR           = r'\|\|'
t_COMMA         = r','
t_DOT           = r'\.'
t_AT            = r'@'
t_QM            = r'\?'
t_TO            = r'=>'
t_ASSIGN        = r'='
t_SCOLON        = r';'
t_APOSTR        = r"\'"
t_ignore_COMMENT = r'\#.*'

keywords_map = {k.lower(): k for k in keywords}

def t_ID(t):
    r'[A-Za-z_][\w_]*'
    t.type = keywords_map.get(t.value,"ID")
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

# Comment (C-Style)
def t_cppcomment(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count('\n')
    #t.lexer.skip(1)

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

###############################################################################

t_ignore = " \t"

def t_NEWLINE(t):
    r'\n'
    t.lexer.lineno += t.value.count("\n")

import ply.lex as lex


def build():
    return lex.lex()
