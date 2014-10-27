#!/usr/bin/env python3

import sync_ast


precedence = (
    ('left', 'LOR', 'LAND', 'BOR', 'BAND', 'BXOR'),
    ('left', 'LE', 'GE', 'GEQ', 'LEQ', 'EQ', 'NEQ'),
    ('nonassoc', 'NOT'),
    ('left', 'MULT', 'DIVIDE', 'MOD', 'SHL', 'SHR'),
    ('right', 'UMINUS'),
)


ast = {}


def p_sync(p):
    '''
    sync : SYNCH ID macros_list_opt LPAREN input_list BOR output_list RPAREN \
           LBRACE decl_list_opt state_list RBRACE
    '''
    ast = sync_ast.Sync(p[2],
                        p[3],
                        sync_ast.PortList(p[5]),
                        sync_ast.PortList(p[7]),
                        p[10],
                        sync_ast.StateList(p[11]))
    p[0] = ast


def p_macros_list_opt(p):
    '''
    macros_list_opt : LBRACKET id_list RBRACKET
                | empty
    '''
    macros = p[2] if p[1] else []
    p[0] = sync_ast.Macros(macros)


def p_id_list(p):
    '''
    id_list : ID
            | id_list COMMA ID
    '''
    p[0] = [sync_ast.ID(p[1])] if len(p) == 2 else p[1] + [sync_ast.ID(p[3])]


def p_input_list(p):
    '''
    input_list : input
               | input_list COMMA input
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_input(p):
    '''
    input : ID
          | ID COLON ID
          | ID COLON NUMBER
    '''
    if len(p) == 4:
        depth = sync_ast.ID(p[3]) if type(p[3]) == 'str' else sync_ast.NUMBER(p[3])
    else:
        depth = sync_ast.DepthNone()

    p[0] = sync_ast.Port(p[1], depth)


def p_output_list(p):
    '''
    output_list : output
                | output_list COMMA output
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_output(p):
    '''
    output : ID
           | ID COLON depth_exp
    '''
    p[0] = sync_ast.Port(p[1], (sync_ast.DepthNone() if len(p) == 2 else p[3]))


def p_depth_exp(p):
    '''
    depth_exp : NUMBER
              | ID
              | ID PLUS NUMBER
              | ID MINUS NUMBER
    '''
    if len(p) == 2:
        p[0] = sync_ast.ID(p[1]) if type(p[1]) == 'str' else sync_ast.NUMBER(p[1])

    else:
        p[0] = sync_ast.DepthExp(p[1], p[3] if p[2] == '+' else -p[3])

def p_decl_list_opt(p):
    '''
    decl_list_opt : decl_list
                  | empty
    '''
    p[0] = sync_ast.DeclList(p[1]) if p[1] != '' else sync_ast.DeclList([])

def p_decl_list(p):
    '''
    decl_list : decl
              | decl_list decl
    '''
    decl_list = p[1] if len(p) == 2 else p[1] + p[2]
    p[0] = decl_list


def p_decl(p):
    '''
    decl : STORE id_list SCOLON
         | STATE type id_list SCOLON
    '''
    if len(p) == 4:
        p[0] = [sync_ast.StoreVar(n.name) for n in p[2]]
    else:
        p[0] = [sync_ast.StateVar(n.name, p[2]) for n in p[3]]


def p_type(p):
    '''
    type : INT LPAREN NUMBER RPAREN
         | ENUM LPAREN id_list RPAREN
    '''
    if p[1] == 'int':
        p[0] = sync_ast.IntType(p[3])
    else:
        p[0] = sync_ast.EnumType(p[3])


def p_state_list(p):
    '''
    state_list : state
               | state_list state
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]


def p_state(p):
    '''
    state : ID LBRACE on_scope elseon_scope_list_opt RBRACE
    '''
    p[0] = sync_ast.State(p[1], [p[3]] + p[4])


def p_on_scope(p):
    '''
    on_scope : ON COLON trans_list
    '''
    p[0] = sync_ast.TransScope(p[3])


def p_elseon_scope_list_opt(p):
    '''
    elseon_scope_list_opt : elseon_scope_list
                          | empty
    '''
    p[0] = p[1] if p[1] != '' else []


def p_elseon_scope_list(p):
    '''
    elseon_scope_list : elseon_scope
                      | elseon_scope_list elseon_scope
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]


def p_elseon_scope(p):
    '''
    elseon_scope : ELSEON COLON trans_list
    '''
    p[0] = sync_ast.TransScope(p[3])


def p_trans_list(p):
    '''
    trans_list : trans_stmt
               | trans_list trans_stmt
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]


def p_trans_stmt(p):
    '''
    trans_stmt : ID condition_opt guard_opt action_list
    '''
    p[0] = sync_ast.Trans(p[1], p[2], p[3], p[4])


def p_condition_opt(p):
    '''
    condition_opt : DOT cond_segmark
                  | DOT cond_datamsg
                  | DOT cond_else
                  | empty
    '''
    if len(p) == 2:
        p[0] = sync_ast.CondEmpty()
    else:
        p[0] = p[2]


def p_cond_segmark(p):
    '''
    cond_segmark : AT ID
    '''
    p[0] = sync_ast.CondSegmark(p[2])


def p_cond_datamsg(p):
    '''
    cond_datamsg : QM ID
                 | LPAREN id_list tail_opt RPAREN
                 | QM ID LPAREN id_list tail_opt RPAREN
    '''
    if len(p) == 3:
        p[0] = sync_ast.CondDataMsg(p[2], [], None)

    elif len(p) == 5:
        p[0] = sync_ast.CondDataMsg(None, p[2], p[3])

    elif len(p) == 7:
        p[0] = sync_ast.CondDataMsg(p[2], p[4], p[5])


def p_tail_opt(p):
    '''
    tail_opt : LOR ID
             | empty
    '''
    p[0] = p[2] if len(p) == 3 else None


def p_cond_else(p):
    '''
    cond_else : ELSE
    '''
    p[0] = sync_ast.CondElse()

def p_guard_opt(p):
    '''
    guard_opt : BAND int_exp
              | empty
    '''
    if p[1] == '':
        code = 'lambda : True'

        try:
            f = eval(code)
        except SyntaxError as err:
            print('guard_opt:', err)
            quit()

        f.code = code
        p[0] = sync_ast.IntExp(f)
    else:
        p[0] = p[2]


def p_action_list(p):
    '''
    action_list : LBRACE set_stmt_opt send_stmt_opt goto_stmt_opt RBRACE
    '''
    p[0] = p[2] + p[3] + p[4]


def p_set_stmt_opt(p):
    '''
    set_stmt_opt : SET assign_list SCOLON
                 | empty
    '''
    p[0] = p[2] if len(p) == 4 else []


def p_assign_list(p):
    '''
    assign_list : assign
                | assign_list COMMA assign
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_assign(p):
    '''
    assign : ID ASSIGN int_exp
           | ID ASSIGN data_exp
    '''
    p[0] = sync_ast.Assign(p[1], p[3])


def p_data_exp(p):
    '''
    data_exp : data
             | LPAREN data RPAREN
    '''
    data = p[1] if len(p) == 2 else p[2]
    p[0] = sync_ast.DataExp(data)


def p_data(p):
    '''
    data : item
         | data LOR item
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_item(p):
    '''
    item : THIS
         | ID
         | APOSTR ID
         | ID COLON rhs
    '''
    if len(p) == 2:
        if p[1] == 'this':
            p[0] = sync_ast.ItemThis()
        else:
            p[0] = sync_ast.ItemVar(p[1])

    elif len(p) == 3:
        p[0] = sync_ast.ItemExpand(p[2])

    elif len(p) == 4:
        p[0] = sync_ast.ItemPair(p[1], p[3])
    else:
        raise ValueError("Something Wrong!")


def p_rhs(p):
    '''
    rhs : ID
        | int_exp
    '''
    p[0] = sync_ast.ID(p[1]) if type(p[1]) == str else p[1]


def p_send_stmt_opt(p):
    '''
    send_stmt_opt : SEND dispatch_list SCOLON
                  | empty
    '''
    p[0] = p[2] if len(p) == 4 else []


def p_dispatch_list(p):
    '''
    dispatch_list : dispatch
                  | dispatch_list COMMA dispatch
    '''
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_dispatch(p):
    '''
    dispatch : msg_exp TO ID
    '''
    p[0] = sync_ast.Send(p[1], p[3])


def p_msg_exp(p):
    '''
    msg_exp : AT int_exp
            | AT ID
            | data_msg
            | NIL
    '''
    if len(p) == 2:
        p[0] = sync_ast.MsgNil() if p[1] == 'nil' else p[1]
    else:
        depth = sync_ast.ID(p[2]) if type(p[2]) == str else p[2]
        p[0] = sync_ast.MsgSegmark(depth)

def p_data_msg(p):
    '''
    data_msg : data_exp
             | QM ID data_exp
    '''
    if len(p) == 2:
        p[0] = sync_ast.MsgData(None, p[1])
    else:
        p[0] = sync_ast.MsgData(p[2], p[3])


def p_goto_stmt_opt(p):
    '''
    goto_stmt_opt : GOTO id_list SCOLON
                  | empty
    '''
    states = [n for n in p[2]] if len(p) == 4 else []
    p[0] = [sync_ast.Goto(states)]


def p_empty(p):
    'empty :'
    p[0] = ''

###############################
# INTEXP

intexp_args = []


def p_int_exp(p):
    '''
    int_exp : LBRACKET intexp_raw RBRACKET
    '''
    global intexp_args
    code = 'lambda {}: {}'.format(', '.join(set(intexp_args)), p[2])

    try:
        f = eval(code)
    except SyntaxError as err:
        print('guard_opt:', err, "\n", code)
        quit()

    f.code = code
    p[0] = sync_ast.IntExp(f)
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
        if p[2] == '&&': p[2] = ' and '
        if p[2] == '||': p[2] = ' or '
        if p[1] == '!': p[1] = ' not '

        p[0] = ''.join(str(t) for t in list(p)[1:])


def p_intexp_id(p):
    '''
    intexp_id : ID
    '''
    global intexp_args
    intexp_args += p[1]
    p[0] = p[1]

###############################


def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value, p.lineno, ':', p.lexpos)
    else:
        print("Syntax error at EOF")
    quit()


import ply.yacc as yacc
import sync_lexer as lexer


def build(start):
    tokens = lexer.tokens
    return yacc.yacc(start=start, debug=0, tabmodule='parsetab/sync')


import inspect
import sys

def linenumber_of_member(m):
    try:
        return m[1].__code__.co_firstlineno
    except AttributeError:
        return -1

def print_grammar():
    rules = []

    members = inspect.getmembers(sys.modules[__name__])
    members = sorted(members, key=linenumber_of_member)
    #print(members)
    #return

    for name, obj in members:
        if inspect.isfunction(obj) and name[:2] == 'p_'\
                and obj.__doc__ is not None:
            rule = str(obj.__doc__).strip()
            rules.append(rule)

    print("\n\n".join(rules))
