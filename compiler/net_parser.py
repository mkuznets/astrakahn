#!/usr/bin/env python3

import collections
import networkx as nx

precedence = (
    ('left', 'PARALLEL'),
    ('left', 'SERIAL'),
)

ast = None

Net = collections.namedtuple('Net', 'type name config_params inputs outputs '
                                    'decls wiring')

Morphism = collections.namedtuple('Morphism', 'name size body override')

Synchroniser = collections.namedtuple('Synchroniser', 'name macros obj')

Override = collections.namedtuple('Override', 'join split synch')

Map = collections.namedtuple('Map', 'box n_inputs')
Join = collections.namedtuple('Join', 'box')
Split = collections.namedtuple('Split', 'box')

SplitMap = collections.namedtuple('SplitMap', 'split map')
MapJoin = collections.namedtuple('MapJoin', 'map join')

Morph_S_M_J = collections.namedtuple('Morph_S_M_J', 'split map join')
Morph_SM_J = collections.namedtuple('Morph_SM_J', 'splitmap join')
Morph_S_MJ = collections.namedtuple('Morph_S_MJ', 'split mapjoin')


def p_start(p):
    '''
    root : net
    '''
    global ast
    ast = p[1]


def p_net(p):
    '''
    net : nettype vertex_name config_params\
          LPAREN in_chans VBAR out_chans RPAREN decls CONNECT wiring END
    '''
    p[0] = Net(p[1], p[2], p[3], p[5], p[7], p[9], p[11])


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
    config_params : LBRACKET id_list RBRACKET
                  | empty
    '''
    p[0] = p[1] if len(p) > 2 else []


def p_id_list(p):
    '''
    id_list : ID
            | id_list COMMA ID
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_kw_list(p):
    '''
    kw_list : ID EQUAL NUMBER
            | kw_list COMMA ID EQUAL NUMBER
    '''
    if len(p) == 4:
        p[0] = {p[1]: p[3]}
    else:
        p[0] = p[1]
        p[0].update({p[1]: p[3]})

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
    decls : decls_list
          | empty
    '''
    if p[1] != '':
        p[0] = {d.name: d for d in p[1]}
    else:
        p[0] = {}


def p_decls_list(p):
    '''
    decls_list : decl
               | decls_list decl
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
    synchroniser : SYNCH ID
                 | SYNCH ID LBRACKET kw_list RBRACKET
    '''
    name = p[2]

    if len(p) == 3:
        p[0] = Synchroniser(name, None, None)
    else:
        p[0] = Synchroniser(name, p[4], None)


def p_morphism(p):
    '''
    morphism : MORPH morph_name LPAREN size RPAREN LBRACE morph_body RBRACE
    '''
    p[0] = Morphism(p[2], p[4], p[7]['decls'], p[7]['override'])


def p_morph_name(p):
    '''morph_name : ID'''
    p[0] = p[1]


def p_size(p):
    '''size : ID'''
    p[0] = p[1]


def p_morph_body(p):
    '''
    morph_body : morph_list
               | morph_list WHERE override_list
    '''
    p[0] = {'decls': p[1], 'override': p[3] if len(p) == 4 else None}


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
    split_map_join : split SLASH LBRACKET map_list RBRACKET SLASH join
    '''
    p[0] = Morph_S_M_J(p[1], p[4], p[7])


def p_splitmap_join(p):
    '''
    splitmap_join : LBRACKET split_map_list RBRACKET SLASH join
    '''
    p[0] = Morph_SM_J(p[2], p[5])


def p_split_mapjoin(p):
    '''
    split_mapjoin : split SLASH LBRACKET map_join_list RBRACKET
    '''
    p[0] = Morph_S_MJ(p[1], p[4])


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
    p[0] = SplitMap(p[1], p[3])


def p_map_join(p):
    '''map_join : map SLASH join'''
    p[0] = MapJoin(p[1], p[3])


def p_map(p):
    '''
    map : ID
        | NUMBER COLON ID
    '''
    if len(p) == 2:
        p[0] = Map(p[1], 1)
    else:
        p[0] = Map(p[3], p[1])


def p_split(p):
    '''split : ID'''
    p[0] = Split(p[1])


def p_join(p):
    '''join : ID'''
    p[0] = Join(p[1])


def p_override_list(p):
    '''
    override_list : override
                  | override_list COMMA override
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_override(p):
    '''override : join SERIAL split EQUAL synch'''
    p[0] = Override(p[1], p[3], p[5])


def p_synch(p):
    '''synch : ID'''
    p[0] = p[1]


def p_wiring(p):
    '''
    wiring : wiring_ast
           | empty
    '''
    p[0] = p[1]

###############################################################################
#
# Parse wiring expression
#

wiring_ast = nx.DiGraph()
cnt = 0


def p_wiring_ast(p):
    '''wiring_ast : wiring_exp'''
    global wiring_ast

    wiring_ast.graph['root'] = cnt - 1
    p[0] = wiring_ast

    # Alloc new graph for further AST.
    wiring_ast = nx.DiGraph()


def p_wiring_exp(p):
    '''
    wiring_exp : wiring_exp PARALLEL wiring_exp
               | wiring_exp SERIAL wiring_exp
               | factor
    '''
    global cnt, wiring_ast

    if len(p) == 2:
        # Identifier/expression/unary operator
        p[0] = p[1]
    else:
        # Binary operator
        wiring_ast.add_node(cnt, {'type': 'operator', 'value': p[2]})
        wiring_ast.add_edge(cnt, p[1])
        wiring_ast.add_edge(cnt, p[3])

        p[0] = cnt
        cnt += 1


def p_factor(p):
    '''
    factor : base STAR
           | base BACKSLASH
           | base
    '''
    global cnt, wiring_ast

    if len(p) == 2:
        # Identifier/expression
        p[0] = p[1]
    else:
        # Unary operator
        wiring_ast.add_node(cnt, {'type': 'operator', 'value': p[2]})
        wiring_ast.add_edge(cnt, p[1])
        p[0] = cnt
        cnt += 1


def p_base(p):
    '''
    base : operand
         | LPAREN wiring_exp RPAREN
    '''
    global cnt, wiring_ast

    if len(p) == 2:
        # New operand.
        p[0] = p[1]

    else:
        # Parenthesized expression.
        p[0] = p[2]


def p_operand(p):
    '''
    operand : ID
            | LE naming VBAR ID VBAR naming GE
    '''
    global cnt, wiring_ast

    if len(p) == 2:
        # Operand as an identifier.
        wiring_ast.add_node(cnt, {'type': 'node', 'value': p[1],
                                  'inputs': {}, 'outputs': {}})
        p[0] = cnt
        cnt += 1

    else:
        # Operand in renaming brackets.
        wiring_ast.add_node(cnt, {'type': 'node', 'value': p[4],
                                  'inputs': p[2], 'outputs': p[6]})
        p[0] = cnt
        cnt += 1


def p_naming(p):
    '''
    naming : id_list
    '''
    p[0] = {i: name for i, name in enumerate(p[1])}

#
###############################################################################


def p_empty(p):
    'empty :'
    p[0] = ''


def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value, p.lineno, ':', p.lexpos)
    else:
        print("Syntax error at EOF")
    quit()

###############################################################################

import sys
import inspect
import ply.yacc as yacc
import net_lexer as lexer


def build():
    tokens = lexer.tokens
    return yacc.yacc(debug=0, tabmodule='parsetab/net')


def print_grammar():
    rules = []

    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isfunction(obj) and name[:2] == 'p_'\
                and obj.__doc__ is not None:
            rule = str(obj.__doc__).strip()
            rules.append(rule)

    print("\n".join(rules))
