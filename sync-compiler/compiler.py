#!/usr/bin/env python3

import collections
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


intexp_args = []

def p_intexp(p):
    '''
    intexp : intexp_raw
    '''
    global intexp_args
    p[0] = 'lambda {}: {}'.format(intexp_args, p[1])
    intexp_args = []

def p_intexp_raw(p):
    '''
    intexp_raw : NUMBER
           | intexp_id
           | LPAREN intexp_raw RPAREN
           | intexp_raw PLUS intexp_raw
           | intexp_raw MINUS intexp_raw
           | intexp_raw MULT intexp_raw
           | intexp_raw DIVIDE intexp_raw
           | intexp_raw MOD intexp_raw
           | intexp_raw SHL intexp_raw
           | intexp_raw SHR intexp_raw
           | intexp_raw BOR intexp_raw
           | intexp_raw BAND intexp_raw
           | intexp_raw BXOR intexp_raw
           | MINUS intexp_raw %prec UMINUS
           | intexp_raw LE intexp_raw
           | intexp_raw GE intexp_raw
           | intexp_raw EQ intexp_raw
           | intexp_raw NEQ intexp_raw
           | intexp_raw LEQ intexp_raw
           | intexp_raw GEQ intexp_raw
           | NOT intexp_raw
           | intexp_raw LAND intexp_raw
           | intexp_raw LOR intexp_raw
    '''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ''.join(str(t) for t in list(p)[1:])

def p_intexp_id(p):
    '''
    intexp_id : ID
    '''
    global intexp_args
    intexp_args += p[1]
    p[0] = p[1]

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
    Condition = collections.namedtuple('Condition', 'condition guard')

    if len(p) == 2:
        p[0] = Condition(p[1], None)
    else:
        p[0] = Condition(p[1], p[3])

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
    if len(p) == 2:
        if p[1] == 'else':
            p[0] = '__else__'
        else:
            p[0] = ('pattern', p[1])
    else:
        if p[1] == '@':
            p[0] = ('segmark', p[2])
        elif p[1] == '?':
            if len(p) == 4:
                p[0] = ('choice_pattern', p[2], p[3])
            else:
                p[0] = ('choice', p[2])

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
    p[0] = (p[1], ) if len(p) == 2 else tuple(p[2])

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
    p[0] = (p[3], p[1])

def p_msgexp(p):
    '''
    msgexp : AT intexp
           | dataexp
           | QM ID dataexp
           | NIL
    '''
    if len(p) == 2:
        if p[1] == 'nil':
            p[0] = '__nil__'
        else:
            p[0] = ('data', p[1])
    else:
        if p[1] == '@':
            p[0] = ('segmark', p[2])
        elif p[1] == '?':
            if len(p) == 4:
                p[0] = ('choice_data', p[2], p[3])
            else:
                p[0] = ('choice', p[2])

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
