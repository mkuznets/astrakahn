#!/usr/bin/env python3

import sys
sys.path.insert(0,"../..")

if sys.version_info[0] >= 3:
    raw_input = input

keywords = ['SYNC', 'STORE', 'STATE', 'INT', 'ENUM', 'ON', 'ELSEON', 'ELSE', 'DO',
            'SEND', 'GOTO', 'THIS', 'NIL']

tokens = keywords + [
    'ID', 'NUMBER', 'LBRACE', 'RBRACE', 'LPAREN', 'RPAREN', 'LBRACKET',
    'RBRACKET', 'COLON', 'PLUS', 'MINUS', 'MULT', 'DIVIDE', 'MOD', 'SHL',
    'SHR', 'LE', 'GE', 'GEQ', 'LEQ', 'EQ', 'NEQ', 'NOT', 'BAND', 'BOR', 'BXOR',
    'LAND', 'LOR', 'COMMA', 'DOT', 'AT', 'QM', 'TO',
    'ASSIGN', 'SCOLON', 'EQUAL'
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
t_EQUAL         = r'='
t_ASSIGN        = r':='
t_SCOLON        = r';'

keywords_map = {k.lower(): k for k in keywords}

def t_ID(t):
    r'[A-Za-z_][\w_]*'
    t.type = keywords_map.get(t.value,"ID")
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
    ('left', 'LOR', 'LAND', 'BOR', 'BAND', 'BXOR'),
    ('left', 'LE', 'GE', 'GEQ', 'LEQ', 'EQ', 'NEQ'),
    ('nonassoc', 'NOT'),
    ('left', 'MULT', 'DIVIDE', 'MOD', 'SHL', 'SHR'),
    ('right', 'UMINUS'),
)

sync = {}

def p_sync(p):
    '''
    sync : SYNC ID params body
         | SYNC ID confs params body
    '''
    if len(p) == 5:
        sync['params'] = p[3]
        sync['body'] = p[4]
    elif len(p) == 6:
        sync['confs'] = p[3]
        sync['params'] = p[4]
        sync['body'] = p[5]

def p_body(p):
    '''
    body : LBRACE decls trans RBRACE
    '''
    p[0] = {'decls': p[2], 'trans': p[3]}

def p_intexp(p):
    '''
    intexp : NUMBER
           | ID
           | LPAREN intexp RPAREN
           | intexp PLUS intexp
           | intexp MINUS intexp
           | intexp MULT intexp
           | intexp DIVIDE intexp
           | intexp MOD intexp
           | intexp SHL intexp
           | intexp SHR intexp
           | intexp BOR intexp
           | intexp BAND intexp
           | intexp BXOR intexp
           | MINUS intexp %prec UMINUS
           | intexp LE intexp
           | intexp GE intexp
           | intexp EQ intexp
           | intexp NEQ intexp
           | intexp LEQ intexp
           | intexp GEQ intexp
           | NOT intexp
           | intexp LAND intexp
           | intexp LOR intexp
    '''
    p[0] = None

def p_empty(p):
    'empty :'
    p[0] = ''

def p_chan(p):
    'chan : ID'
    p[0] = p[1]

def p_var(p):
    'var : ID'
    p[0] = p[1]

def p_chantail(p):
    '''
    chantail : ID
    '''
    p[0] = p[1]

def p_shift(p):
    '''
    shift : NUMBER
          | conf
    '''
    p[0] = p[1]

def p_type(p):
    '''
    type : INT LPAREN NUMBER RPAREN
         | ENUM LPAREN id_list RPAREN
    '''
    p[0] = (p[1], p[3])

def p_id_list(p):
    '''
    id_list : ID
            | id_list COMMA ID
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_conf(p):
    'conf : ID'
    p[0] = p[1]


def p_confs(p):
    'confs : LBRACKET confs_list RBRACKET'
    p[0] = p[2]

def p_confs_list(p):
    '''
    confs_list : conf
               | confs_list COMMA conf
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_params(p):
    'params : LPAREN inparams BOR outparams RPAREN'
    p[0] = {'in': p[2], 'out': p[4]}

def p_inparams(p):
    '''
    inparams : inparam
             | inparams COMMA inparam
             | empty
    '''
    if len(p) == 2:
        p[0] = [p[1]] if p[1] != '' else []
    elif len(p) == 4:
         p[0] = p[1] + [p[3]]

def p_inparam(p):
    '''
    inparam : chan
            | chan COLON indepth
    '''
    p[0] = (p[1], None) if len(p) == 2 else (p[1], p[3])

def p_indepth(p):
    '''
    indepth : var
            | NUMBER
    '''
    if type(p[1]) == int:
        p[0] = eval('lambda : {}'.format(p[1]))
    else:
        p[0] = eval('lambda {} : {}'.format(p[1], p[1]))

def p_outparams(p):
    '''
    outparams : outparam
              | outparams COMMA outparam
              | empty
    '''
    if len(p) == 2:
        p[0] = [p[1]] if p[1] != '' else []
    elif len(p) == 4:
         p[0] = p[1] + [p[3]]

def p_outparam(p):
    '''
    outparam : chan
             | chan COLON depthexp
    '''
    p[0] = (p[1], None) if len(p) == 2 else (p[1], p[3])

def p_depthexp(p):
    '''
    depthexp : NUMBER
             | var
             | var PLUS shift
             | var MINUS shift
    '''
    if len(p) == 2:
        if type(p[1]) == int:
            p[0] = eval('lambda : {}'.format(p[1]))
        else:
            p[0] = eval('lambda {} : {}'.format(p[1], p[1]))

    elif len(p) == 4:
        exp = list(p)[1:]
        if type(p[3]) == int:
            p[0] = eval('lambda {} : {} {} {}'.format(p[1], *exp))
        else:
            p[0] = eval('lambda {} {} : {} {} {}'.format(p[1], p[3], *exp))

def p_decls(p):
    '''
    decls : storedecls
          | statedecls
          | decls storedecls
          | decls statedecls
          | empty
    '''
    if p[1] == '':
        p[0] = []
    else:
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]

def p_storedecls(p):
    '''
    storedecls : STORE storedecl SCOLON
    '''
    p[0] = (p[1], '', p[2])

def p_statedecls(p):
    '''
    statedecls : STATE type statedecl SCOLON
    '''
    p[0] = (p[1], p[2], p[3])

def p_storedecl(p):
    '''
    storedecl : var COLON chantail
              | storedecl COMMA var COLON chantail
    '''
    p[0] = [(p[1], p[3])] if len(p) == 4 else p[1] + [(p[3], p[5])]

def p_statedecl(p):
    '''
    statedecl : var
              | statedecl COMMA var
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_trans(p):
    '''
    trans : label trans_list
          | trans label trans_list
    '''
    p[0] = [(p[1], p[2])] if len(p) == 3 else p[1] + [(p[2], p[3])]

def p_label(p):
    '''
    label : ID COLON
    '''
    p[0] = p[1]

def p_trans_list(p):
    '''
    trans_list : trans_stmt SCOLON
               | trans_list trans_stmt SCOLON
    '''
    p[0] = [p[1]] if len(p) == 3 else p[1] + [p[2]]

def p_trans_stmt(p):
    '''
    trans_stmt : on_clause do_clause send_clause goto_clause
    '''
    print('TRANS_STMT:', list(p))

def p_on_clause(p):
    '''
    on_clause : ON chancond
              | ELSEON chancond
    '''
    p[0] = (p[1], p[2])

def p_chancond(p):
    '''
    chancond : primary
             | primary LAND intexp
    '''
    if len(p) == 2:
        p[0] = (p[1], None)
    else:
        p[0] = (p[1], p[3])

def p_primary(p):
    '''
    primary : chan DOT secondary
            | chan
    '''
    if len(p) == 2:
        p[0] = (p[1], None)
    else:
        p[0] = (p[1], p[3])

def p_secondary(p):
    '''
    secondary : AT ID
              | ELSE
              | QM ID
              | pattern
              | QM ID pattern
    '''
    t = None
    if len(p) == 2:
        if p[1] == 'else':
            t = {'choice': None, 'pattern': None, 'segmark' : None}
        else:
            t = {'choice': None, 'pattern': p[1], 'segmark' : None}
    else:
        if p[1] == '@':
            t = {'choice': None, 'pattern': None, 'segmark' : p[2]}
        elif p[1] == '?':
            t = {'choice': p[2],
                 'pattern': p[3] if len(p) == 4 else None,
                 'segmark' : None}
    p[0] = ('guard' if p[1] != 'else' else 'else', t)

def p_pattern(p):
    '''
    pattern : LPAREN id_list opttail RPAREN
    '''
    p[0] = (p[2], p[3])

def p_opttail(p):
    '''
    opttail : empty
            | LOR ID
    '''
    p[0] = p[2] if len(p) == 3 else None

def p_do_clause(p):
    '''
    do_clause : DO assign
              | do_clause COMMA assign
              | empty
    '''
    if p[1] == '':
        p[0] = []
    else:
        p[0] = [p[2]] if len(p) == 3 else p[1] + [p[3]]

def p_assign(p):
    '''
    assign : ID ASSIGN intexp
           | ID ASSIGN dataexp
    '''
    p[0] = (p[1], p[3])

def p_dataexp(p):
    '''
    dataexp : pm
            | LPAREN pm_list RPAREN
    '''
    p[0] = [p[1]] if len(p) == 2 else p[2]

def p_pm_list(p):
    '''
    pm_list : pm
            | pm_list COMMA pm
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_pm(p):
    '''
    pm : THIS
       | var ASSIGN intexp
       | var
    '''
    if len(p) == 1:
        p[0] = '__this__' if p[1] == 'this' else p[1]
    else:
        p[0] = {p[1]: p[3]}


def p_send_clause(p):
    '''
    send_clause : SEND dispatch_list
                | empty
    '''
    p[0] = p[2] if len(p) == 3 else []

def p_dispatch_list(p):
    '''
    dispatch_list : dispatch
                  | dispatch_list COMMA dispatch
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

def p_dispatch(p):
    '''
    dispatch : msgexp TO chan
    '''
    p[0] = (p[1], p[3])

def p_msgexp(p):
    '''
    msgexp : AT intexp
           | dataexp
           | QM ID dataexp
           | NIL
    '''
    t = None
    if len(p) == 2:
        if p[1] == 'nil':
            t = {'choice': None, 'pattern': None, 'segmark' : None}
        else:
            t = {'choice': None, 'pattern': p[1], 'segmark' : None}
    else:
        if p[1] == '@':
            t = {'choice': None, 'pattern': None, 'segmark' : p[2]}
        elif p[1] == '?':
            t = {'choice': p[2],
                 'pattern': p[3] if len(p) == 4 else None,
                 'segmark' : None}
    p[0] = ('msg' if p[1] != 'nil' else 'nil', t)

def p_goto_clause(p):
    '''
    goto_clause : GOTO id_list
                | empty
    '''
    p[0] = p[2] if len(p) > 2 else []

def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value)
    else:
        print("Syntax error at EOF")

import ply.yacc as yacc
yacc.yacc()

with open('tests/reg.t', 'r') as sync_file:
    sync_code = sync_file.read()

yacc.parse(sync_code)

print(sync)
