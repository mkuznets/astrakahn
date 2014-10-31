#!/usr/bin/env python3

import os
import sys
import sync_lexer as lex
import sync_parser as parse

import sync_ast

sys.path[0:0] = ['..']

import sync as sync_runtime


class MacroLexer:

    def __init__(self, lexer, macros={}):
        self.lexer = lexer
        self.macros = macros

    def token(self):
        t = self.lexer.token()
        if t is not None \
                and self.macros \
                and t.type == 'ID' and t.value in self.macros:
            t.value = self.macros[t.value]
        return t

    def input(self, code):
        self.lexer.input(code)


class SyncBuilder(sync_ast.NodeVisitor):

    def __init__(self):

        # Mapping from port names to port ids.
        self.input_index = None
        self.output_index = None

    def visit_Sync(self, node, children):
        return sync_runtime.Sync(name=node.name, **children)

    #--------------------------------------------------

    def visit_PortList(self, node, children):

        index = {n: i for i, n in enumerate(children['ports'])}

        if self.input_index is None:
            self.input_index = index
        else:
            self.output_index = index

        return children['ports']

    def visit_Port(self, node, children):
        return node.name

    def visit_DepthExp(self, node, _):
        return (node.depth, node.shift)

    def visit_DepthNone(self, node, _):
        return None

    #--------------------------------------------------

    def visit_DeclList(self, node, children):
        return children['decls']

    def visit_StoreVar(self, node, _):
        return sync_runtime.StoreVar(node.name)

    def visit_StateVar(self, node, children):
        type, arg = children['type']

        assert(type == 'int' or type == 'enum')

        if type == 'int':
            return sync_runtime.StateInt(node.name, arg)
        elif type == 'enum':
            return sync_runtime.StateEnum(node.name, arg)

    def visit_IntType(self, node, _):
        return ('int', node.size)

    def visit_EnumType(self, node, children):
        return ('enum', children['labels'])

    #--------------------------------------------------

    def visit_StateList(self, node, children):
        return children['states']

    def visit_State(self, node, children):
        byport = {}

        for i, order in enumerate(children['trans_orders']):
            for trans in order:
                trans.order = i
                byport[trans.port] = byport.get(trans.port, []) + [trans]

        handlers = [sync_runtime.PortHandler(p, t) for p, t in byport.items()]

        return sync_runtime.State(node.name, handlers)

    def visit_TransOrder(self, node, children):
        return children['trans_stmt']

    def visit_Trans(self, node, children):
        pid = self.input_index[node.port]

        return sync_runtime.Transition(pid, children['condition'],
                                       children['guard'], children['actions'])

    #--------------------------------------------------

    def visit_CondSegmark(self, node, _):
        return ('CondSegmark', node.depth)

    def visit_CondDataMsg(self, node, children):
        return ('CondDataMsg', node.choice, children['labels'], node.tail)

    def visit_CondEmpty(self, node, _):
        return ('CondEmpty', )

    def visit_CondElse(self, node, _):
        return ('CondElse', )

    #--------------------------------------------------

    def visit_Assign(self, node, children):
        return ('Assign', node.lhs, children['rhs'])

    def visit_Send(self, node, children):
        pid = self.output_index[node.port]
        return ('Send', children['msg'], pid)

    def visit_Goto(self, node, children):
        return ('Goto', children['states'])

    #--------------------------------------------------

    def visit_DataExp(self, node, children):
        return ('DataExp', children['items'])

    def visit_ItemThis(self, node, _):
        return ('ItemThis', )

    def visit_ItemVar(self, node, _):
        return ('ItemVar', node.name)

    def visit_ItemExpand(self, node, ):
        return ('ItemPair', node.name, node.name)

    def visit_ItemPair(self, node, children):
        return ('ItemPair', node.label, children['value'])

    #--------------------------------------------------

    def visit_MsgSegmark(self, node, children):

        if type(children['depth']) == 'str':
            depth = ('DepthVar', children['depth'])
        else:
            depth = children['depth']

        return ('MsgSegmark', depth)

    def visit_MsgData(self, node, children):
        return ('MsgData', node.choice, children['data_exp'])

    def visit_MsgNil(self, node, _):
        return ('MsgNil', )

    #--------------------------------------------------

    def visit_IntExp(self, node, _):
        return ('IntExp', node.exp)

    def visit_ID(self, node, _):
        return node.name

    def visit_NUMBER(self, node, _):
        return node.value

    #--------------------------------------------------

    def generic_visit(self, node, _):
        print(node)


def build(src_file, macros={}):

    if not (os.path.isfile(src_file) and os.access(src_file, os.R_OK)):
        raise ValueError('File either does not exist or cannot be read.')

    sync_file = open(src_file, 'r')
    sync_code = sync_file.read()

    lexer = MacroLexer(lex.build(), macros)

    parser = parse.build('sync')
    ast = parser.parse(sync_code, lexer=lexer)

    visitor = SyncBuilder()
    sync_obj = visitor.traverse(ast)

    return sync_obj

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Provide source file!')
        quit()

    ast = build(sys.argv[1])
    ast.show(attrnames=True, nodenames=True)
