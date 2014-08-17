#!/usr/bin/env python3

import os.path
import sys
sys.path.insert(0, '../..')

if sys.version_info[0] >= 3:
    raw_input = input

keywords = ['NET', 'PURENET', 'CONNECT', 'END', 'MORPH', 'WHERE']

tokens = keywords + [
    'ID', 'NUMBER', 'SERIAL', 'PARALLEL', 'STAR', 'BACKSLASH', 'COMMA', 'VBAR',
    'LE', 'GE', 'LPAREN', 'RPAREN', 'LBRACKET', 'RBRACKET', 'SLASH', 'EQUAL',
    'LBRACE', 'RBRACE', 'COLON'
]

# Tokens

# net operators
t_SERIAL        = r'\.\.'
t_PARALLEL      = r'\|\|'
t_STAR          = r'\*'
t_BACKSLASH     = r'\\'

t_COMMA         = r','
t_VBAR      = r'\|'
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

# Build the lexer
import ply.lex as lex
lex.lex()


#with open('tests/reg.t', 'r') as sync_file:
#    sync_code = sync_file.read()

# Give the lexer some input
#lexer = lex.lex()
#lexer.input(sync_code)
#
## Tokenize
#while True:
#    tok = lexer.token()
#    if not tok:
#        break      # No more input
#    print(tok)
#
#quit()

# Parsing rules

precedence = (
#    ('left', 'LOR', 'LAND', 'BOR', 'BAND', 'BXOR'),
#    ('left', 'LE', 'GE', 'GEQ', 'LEQ', 'EQ', 'NEQ'),
#    ('nonassoc', 'NOT'),
#    ('left', 'MULT', 'DIVIDE', 'MOD', 'SHL', 'SHR'),
#    ('right', 'UMINUS'),
)

net_ast = None

def p_start(p):
    '''
    root : net
    '''
    net_ir = p[1]

def p_net(p):
    '''
    net : nettype vertex_name LBRACKET config_params RBRACKET\
          LPAREN in_chans VBAR out_chans RPAREN decls CONNECT wiring END
    '''
    print(list(p))

def p_nettype(p):
    '''
    nettype : NET
            | PURENET
    '''
    p[0] = p[1]

def p_vertex_name(p):
    '''
    vertex_name : ID
    '''
    p[0] = p[1]

def p_config_params(p):
    '''
    config_params : id_list
    '''
    p[0] = p[1]

def p_id_list(p):
    '''
    id_list : ID
            | id_list COMMA ID
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_in_chans(p):
    '''
    in_chans : id_list
    '''
    p[0] = p[1]

def p_out_chans(p):
    '''
    out_chans : id_list
    '''
    p[0] = p[1]

def p_decls(p):
    '''
    decls : decl
          | decls decl
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]

def p_decl(p):
    '''
    decl : net
         | synchroniser
         | morphism
    '''
    p[0] = p[1]

def p_synchroniser(p):
    '''
    synchroniser : ID
    '''
    p[0] = p[1]

def p_morphism(p):
    '''
    morphism : MORPH LPAREN size RPAREN LBRACE morph_body RBRACE
    '''
    p[0] = None

def p_size(p):
    '''size : ID'''
    p[0] = p[1]

def p_morph_body(p):
    '''
    morph_body : morph_list
               | morph_list WHERE override_list
    '''
    body = {'morphs': p[1]}

    if len(2) == 4:
        body['override'] = p[3]

    p[0] = body

def p_morph_list(p):
    '''
    morph_list : morph
               | morph_list COMMA morph
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_morph(p):
    '''
    morph : split_map_join
          | splitmap_join
          | split_mapjoin
    '''
    p[0] = p[1]

def p_split_map_join(p):
    '''
    split_map_join : split SLASH map_list SLASH join
    '''
    p[0] = ('s-m-j', p[1], p[3], p[5])

def p_splitmap_join(p):
    '''
    splitmap_join : split_map_list SLASH join
    '''
    p[0] = ('sm-j', p[1], p[3])

def p_split_mapjoin(p):
    '''
    split_mapjoin : split SLASH map_join_list
    '''
    p[0] = ('s-mj', p[1], p[3])

def p_map_list(p):
    '''
    map_list : map
             | map_list COMMA map
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_split_map_list(p):
    '''
    split_map_list : split_map
                   | split_map_list COMMA split_map
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_map_join_list(p):
    '''
    map_join_list : map_join
                  | map_join_list COMMA map_join
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_split_map(p):
    '''split_map : split SLASH map'''
    p[0] = (p[1], p[3])

def p_map_join(p):
    '''map_join : map SLASH join'''
    p[0] = (p[1], p[3])

def p_map(p):
    '''
    map : ID
        | NUMBER COLON ID
    '''
    if len(p) == 2:
        p[0] = (p[1], 1)
    else:
        p[0] = (p[3], p[1])

def p_split(p):
    '''split : ID'''
    p[0] = p[1]

def p_join(p):
    '''join : ID'''
    p[0] = p[1]

def p_override_list(p):
    '''
    override_list : override
                  | override_list COMMA override
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_override(p):
    '''override : join SERIAL split EQUAL synch'''
    p[0] = (p[1], p[3], p[5])

def p_synch(p):
    '''synch : ID'''
    p[0] = p[1]

def p_wiring(p):
    # TODO
    '''
    wiring : empty
    '''
    p[0] = p[1]

def p_empty(p):
    'empty :'
    p[0] = ''

def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value)
    else:
        print("Syntax error at EOF")

import ply.yacc as yacc
yacc.yacc()

if len(sys.argv) < 2:
    print('USAGE: {} source'.format(sys.argv[0]))
    quit()

filename = sys.argv[1]

if not os.path.isfile(filename):
    print('Source file does not exist.')
    quit()


with open(filename, 'r') as source_file:
    source_code = source_file.read()

yacc.parse(source_code)

print(net_ast)
