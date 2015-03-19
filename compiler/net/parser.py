#!/usr/bin/env python3

import os
from . import ast


precedence = (
    ('left', 'PARALLEL'),
    ('left', 'SERIAL'),
    ('right', 'STAR'),
    ('right', 'BACKSLASH'),
)


def p_net(p):
    '''
    net : pure_opt NET ID LPAREN port_list VBAR port_list RPAREN decl_list_opt \
        CONNECT wiring END
    '''
    p[0] = ast.Net(is_pure=bool(p[1]), name=p[3],
                   inputs=ast.PortList(p[5]),
                   outputs=ast.PortList(p[7]),
                   decls=p[9], wiring=p[11])


def p_port_list(p):
    '''
    port_list : ID
              | port_list COMMA ID
    '''
    p[0] = [ast.ID(p[1])] if len(p) == 2 else p[1] + [ast.ID(p[3])]


def p_pure_opt(p):
    '''
    pure_opt : PURE
             | empty
    '''
    p[0] = p[1]


def p_id_list(p):
    '''
    id_list : ID
            | id_list COMMA ID
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_kwarg_list(p):
    '''
    kwarg_list : ID EQUAL kwvalue
               | kwarg_list COMMA ID EQUAL kwvalue
    '''
    if len(p) == 4:
        p[0] = {p[1]: p[3]}
    else:
        p[0] = p[1]
        p[0].update({p[3]: p[5]})

def p_kwvalue(p):
    '''
    kwvalue : ID
            | NUMBER
    '''
    p[0] = p[1]


def p_decl_list_opt(p):
    '''
    decl_list_opt : decls_list
                  | empty
    '''
    p[0] = ast.DeclList(p[1] or [])


def p_decls_list(p):
    '''
    decls_list : decl
               | decls_list decl
    '''
    p[0] = p[1] if len(p) == 2 else p[1] + p[2]


def p_decl(p):
    '''
    decl : net
         | synchroniser
         | synchtab
         | morphism
    '''
    p[0] = p[1] if type(p[1]) == list else [p[1]]


def p_synchtab(p):
    '''
    synchtab : TAB LBRACKET id_list RBRACKET synchroniser
    '''
    p[0] = ast.SynchTab(p[3], p[5])

def p_synchroniser(p):
    '''
    synchroniser : SYNCH ID macros_opt
    '''
    p[0] = ast.Synchroniser(p[2], p[3], None)


def p_macros_opt(p):
    '''
    macros_opt : LBRACKET kwarg_list RBRACKET
               | empty
    '''
    p[0] = p[2] if p[1] != '' else {}


def p_morphism(p):
    '''
    morphism : MORPH LBRACE morph_body RBRACE
    '''
    p[0] = [ast.Morphism(*m) for m in p[3]]


def p_morph_body(p):
    '''
    morph_body : morph_list
    '''

    morph_body = []
    for m in p[1]:
        morph_body.append(m)

    p[0] = morph_body


def p_morph_list(p):
    '''
    morph_list : morph
               | morph_list COMMA morph
    '''
    p[0] = p[1] if len(p) == 2 else p[1] + p[3]


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
    p[0] = [(p[1], m, p[5]) for m in p[3]]


def p_splitmap_join(p):
    '''
    splitmap_join : LPAREN split_map_list RPAREN SLASH join
    '''
    p[0] = [sm + (p[5], ) for sm in p[2]]


def p_split_mapjoin(p):
    '''
    split_mapjoin : split SLASH LPAREN map_join_list RPAREN
    '''
    p[0] = [(p[1], ) + mj for mj in p[4]]


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
    '''map : ID'''
    p[0] = p[1]


def p_split(p):
    '''split : ID'''
    p[0] = p[1]


def p_join(p):
    '''join : ID'''
    p[0] = p[1]

def p_wiring(p):
    '''
    wiring : wiring_exp
           | wiring PARALLEL wiring
           | wiring SERIAL wiring
           | wiring BACKSLASH
           | wiring STAR
    '''
    if len(p) == 2:
        p[0] = p[1]

    elif len(p) == 4:
        p[0] = ast.BinaryOp(p[2], p[1], p[3])

    else:
        p[0] = ast.UnaryOp(p[2], p[1])


def p_wiring_exp(p):
    '''
    wiring_exp : vertex
               | LPAREN wiring RPAREN
    '''
    p[0] = p[1] if len(p) == 2 else p[2]


def p_vertex(p):
    '''
    vertex : vertex_name
           | LE renaming_opt VBAR vertex_name_or_merge VBAR renaming_opt GE
    '''

    if len(p) == 2:
        p[0] = ast.Vertex(inputs={}, outputs={}, **p[1])

    else:
        p[0] = ast.Vertex(inputs=p[2], outputs=p[6], **p[4])


def p_vertex_name_or_merge(p):
    '''
    vertex_name_or_merge : vertex_name
                         | MERGE
    '''
    if p[1] == '~':
        p[0] = {'name': '~', 'category': None}
    else:
        p[0] = p[1]


def p_vertex_name(p):
    '''
    vertex_name : ID
                | ID COLON ID
    '''
    p[0] = {'name': p[1] if len(p) == 2 else p[3],
            'category': p[1] if len(p) == 4 else None}


def p_renaming_opt(p):
    '''
    renaming_opt : id_list
                 | kwarg_list
                 | empty
    '''
    if not p[1]:
        p[0] = {}
    elif type(p[1]) == list:
        p[0] = dict(enumerate(p[1]))
    else:
        p[0] = p[1]


#------------------------------------------------------------------------------


def p_empty(p):
    'empty :'
    p[0] = ''


def p_error(p):
    if p:
        print('Syntax error at `%s\'' % p.value, p.lineno, ':', p.lexpos)
    else:
        print('Syntax error at EOF')

###############################################################################

import sys
import inspect
import ply.yacc as yacc
from . import lexer


def build():
    tokens = lexer.tokens
    tab_path = os.path.dirname(os.path.realpath(__file__)) + '/parsetab/sync'
    return yacc.yacc(start='net', debug=0, tabmodule=tab_path)


def print_grammar():
    rules = []

    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isfunction(obj) and name[:2] == 'p_'\
                and obj.__doc__ is not None:
            rule = str(obj.__doc__).strip()
            rules.append(rule)

    print("\n".join(rules))
