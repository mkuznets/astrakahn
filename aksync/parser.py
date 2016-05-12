from . import ast

precedence = (
    ('left', 'LOR', 'LAND', 'BOR', 'BAND', 'BXOR'),
    ('left', 'LE', 'GE', 'GEQ', 'LEQ', 'EQ', 'NEQ'),
    ('nonassoc', 'NOT'),
    ('left', 'MULT', 'DIVIDE', 'MOD', 'SHL', 'SHR'),
    ('right', 'UMINUS'),
)


def p_file(p):
    """
    file : sync
         | file sync
    """
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]


def p_sync(p):
    """
    sync : SYNC ID LPAREN id_list BOR id_list RPAREN \
           LBRACE decl_list_opt state_list RBRACE
    """
    p[0] = ast.Sync(p[2], p[4], p[6], p[9], ast.StateList(p[10]))


def p_id_list(p):
    """
    id_list : ID
            | id_list COMMA ID
    """
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_decl_list_opt(p):
    """
    decl_list_opt : decl_list
                  | empty
    """
    p[0] = ast.DeclList(p[1]) if p[1] != '' else ast.DeclList([])


def p_decl_list(p):
    """
    decl_list : decl
              | decl_list decl
    """
    p[0] = p[1] if len(p) == 2 else p[1] + p[2]


def p_decl(p):
    """
    decl : STORE id_list SCOLON
         | STATE type statevar_list SCOLON
    """
    if len(p) == 4:
        p[0] = [ast.StoreVar(n) for n in p[2]]
    else:
        p[0] = [ast.StateVar(n[0], p[2], n[1]) for n in p[3]]


def p_type(p):
    """
    type : INT LPAREN NUMBER RPAREN
    """
    p[0] = ast.IntType(p[3])


def p_statevar_list(p):
    """
    statevar_list : statevar
                  | statevar_list COMMA statevar
    """
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_statevar(p):
    """
    statevar : ID
             | ID ASSIGN NUMBER
    """
    p[0] = (p[1], 0 if len(p) == 2 else p[3])


def p_state_list(p):
    """
    state_list : state
               | state_list state
    """
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]


def p_state(p):
    """
    state : ID LBRACE on_scope elseon_scope_list_opt RBRACE
    """
    p[0] = ast.State(p[1], [p[3]] + p[4])


def p_on_scope(p):
    """
    on_scope : ON COLON trans_list
    """
    p[0] = ast.TransOrder(p[3])


def p_elseon_scope_list_opt(p):
    """
    elseon_scope_list_opt : elseon_scope_list
                          | empty
    """
    p[0] = p[1] if p[1] != '' else []


def p_elseon_scope_list(p):
    """
    elseon_scope_list : elseon_scope
                      | elseon_scope_list elseon_scope
    """
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]


def p_elseon_scope(p):
    """
    elseon_scope : ELSEON COLON trans_list
    """
    p[0] = ast.TransOrder(p[3])


def p_trans_list(p):
    """
    trans_list : trans_stmt
               | trans_list trans_stmt
    """
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]


def p_trans_stmt(p):
    """
    trans_stmt : ID condition_opt guard_opt action_list
    """
    p[0] = ast.Trans(p[1], p[2], p[3], p[4])


def p_condition_opt(p):
    """
    condition_opt : DOT cond_msg
                  | DOT cond_else
                  | empty
    """
    if len(p) == 2:
        p[0] = ast.CondEmpty()
    else:
        p[0] = p[2]


def p_cond_else(p):
    """
    cond_else : ELSE
    """
    p[0] = ast.CondElse()


def p_cond_msg(p):
    """
    cond_msg : AT ID pattern_opt
             | pattern_opt
    """

    if len(p) == 4:
        p[0] = ast.CondSegmark(depth=p[2], **p[3])

    else:
        p[0] = ast.CondDataMsg(**p[1])


def p_pattern_opt(p):
    """
    pattern_opt : LPAREN id_list_opt tail_opt RPAREN
                | empty
    """
    pattern, tail = (p[2], p[3]) if len(p) > 2 else ([], None)
    p[0] = {'pattern': pattern, 'tail': tail}


def p_id_list_opt(p):
    """
    id_list_opt : id_list
                | empty
    """
    p[0] = p[1] or []


def p_tail_opt(p):
    """
    tail_opt : LOR ID
             | empty
    """
    p[0] = p[2] if len(p) == 3 else None


def p_guard_opt(p):
    """
    guard_opt : BAND int_exp
              | empty
    """
    if p[1] == '':
        p[0] = ast.IntExp('True', [], {})

    else:
        p[0] = p[2]


def p_action_list(p):
    """
    action_list : LBRACE set_stmt_opt send_stmt_opt goto_stmt_opt RBRACE
    """
    p[0] = p[2] + p[3] + p[4]


def p_set_stmt_opt(p):
    """
    set_stmt_opt : SET assign_list SCOLON
                 | empty
    """
    p[0] = p[2] if len(p) == 4 else []


def p_assign_list(p):
    """
    assign_list : assign
                | assign_list COMMA assign
    """
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_assign(p):
    """
    assign : ID ASSIGN int_exp
           | ID ASSIGN data_exp
    """
    p[0] = ast.Assign(p[1], p[3])


def p_data_exp(p):
    """
    data_exp : term_list
             | LPAREN term_list RPAREN
             | LBRACE term_list RBRACE
    """
    data = p[1] if len(p) == 2 else p[2]
    p[0] = ast.DataExp(data)


def p_term_list(p):
    """
    term_list : term
              | term_list LOR term
    """
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_term(p):
    """
    term : THIS
         | ID
         | APOSTR ID
         | ID COLON pair_value
    """
    if len(p) == 2:
        if p[1] == 'this':
            p[0] = ast.ItemThis()
        else:
            p[0] = ast.ItemVar(p[1])

    elif len(p) == 3:
        p[0] = ast.ItemExpand(p[2])

    elif len(p) == 4:
        p[0] = ast.ItemPair(p[1], p[3])


def p_pair_value(p):
    """
    pair_value : ID
               | int_exp
    """
    if type(p[1]) is str:
        p[0] = ast.ItemVar(p[1])

    else:
        p[0] = p[1]


def p_send_stmt_opt(p):
    """
    send_stmt_opt : SEND dispatch_list SCOLON
                  | empty
    """
    p[0] = p[2] if len(p) == 4 else []


def p_dispatch_list(p):
    """
    dispatch_list : dispatch
                  | dispatch_list COMMA dispatch
    """
    p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]


def p_dispatch(p):
    """
    dispatch : msg_exp TO ID
    """
    p[0] = ast.Send(p[1], p[3])


def p_msg_exp(p):
    """
    msg_exp : AT int_exp
            | AT int_exp LBRACE data_exp RBRACE
            | data_exp
    """
    if len(p) == 3:
        p[0] = ast.MsgSegmark(p[2], ast.DataExp([]))

    elif len(p) == 6:
        p[0] = ast.MsgSegmark(p[2], p[4])

    else:
        p[0] = ast.MsgRecord(p[1])


def p_goto_stmt_opt(p):
    """
    goto_stmt_opt : GOTO ID SCOLON
                  | empty
    """
    p[0] = [ast.Goto(p[2])] if len(p) == 4 else []


def p_empty(p):
    """
    empty :
    """
    p[0] = ''

###############################
# INTEXP

intexp_args = []
terms = {}
terms_cnt = 1


def p_int_exp(p):
    """
    int_exp : LBRACKET intexp_raw RBRACKET
    """
    global intexp_args, terms, terms_cnt

    p[0] = ast.IntExp(p[2], intexp_args, terms)

    # Cleanup globals
    intexp_args = []
    terms = {}
    terms_cnt = 0


def p_intexp_raw(p):
    """
    intexp_raw : NUMBER
           | exp_term
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
    """
    global terms, terms_cnt

    if len(p) == 2:
        t = ('t%d:d' if type(p[1]) is int else 't%d:s') % terms_cnt
        terms_cnt += 1
        # Ugly hack. Need to make a separate rule for wrapping a number.
        terms[t[:-2]] = p[1]
        p[0] = '{%s}' % t

    else:
        if p[2] == '&&':
            p[2] = ' and '

        if p[2] == '||':
            p[2] = ' or '

        if p[1] == '!':
            p[1] = ' not '

        p[0] = ''.join(str(t) for t in list(p)[1:])


def p_exp_term(p):
    """
    exp_term : ID
    """
    global intexp_args
    intexp_args.append(p[1])
    p[0] = p[1]

###############################


def p_error(p):
    if p:
        print("Syntax error at '%s'" % p.value, p.lineno, ':', p.lexpos)
    else:
        print("Syntax error at EOF")
    quit()


def build():
    import ply.yacc as yacc
    from . import lexer

    tokens = lexer.tokens
    tab_path = 'synctab'
    return yacc.yacc(start='file', debug=0, tabmodule=tab_path)


def linenumber_of_member(m):
    try:
        return m[1].__code__.co_firstlineno
    except AttributeError:
        return -1


def print_grammar():
    import inspect
    import sys

    rules = []

    members = inspect.getmembers(sys.modules[__name__])
    members = sorted(members, key=linenumber_of_member)

    for name, obj in members:
        if inspect.isfunction(obj) and name.startswith('p_') and obj.__doc__:
            rule = str(obj.__doc__).strip()
            rules.append(rule)

    print("\n\n".join(rules))
