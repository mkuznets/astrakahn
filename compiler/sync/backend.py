#!/usr/bin/env python3

import components
from . import ast


class SyncBuilder(ast.NodeVisitor):

    def __init__(self):

        # Mapping from port names to port ids.
        self.input_index = None
        self.output_index = None

        self.consts = []

    def visit_Sync(self, node, children):

        scope = components.Scope(children['decls'] + self.consts)

        del children['decls']
        return components.Sync(name=node.name, scope=scope, **children)

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
        return components.StoreVar(node.name)

    def visit_StateVar(self, node, children):
        type, arg = children['type']

        assert(type == 'int' or type == 'enum')

        if type == 'int':
            return components.StateInt(node.name, arg)
        elif type == 'enum':
            return components.StateEnum(node.name, arg)

    def visit_IntType(self, node, _):
        return ('int', node.size)

    def visit_EnumType(self, node, children):

        # Named constants from enum type.
        for i, label in enumerate(children['labels']):
            c = components.Const(label, i)
            self.consts.append(c)

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

        handlers = [components.PortHandler(p, t) for p, t in byport.items()]

        return components.State(node.name, handlers)

    def visit_TransOrder(self, node, children):
        return children['trans_stmt']

    def visit_Trans(self, node, children):
        pid = self.input_index[node.port]

        return components.Transition(pid, children['condition'],
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

    def visit_ItemExpand(self, node, _):
        return ('ItemPair', node.name, ('ID', node.name))

    def visit_ItemPair(self, node, children):
        if type(children['value']) == str:
            rhs = ('ID', children['value'])
        else:
            rhs = children['value']

        return ('ItemPair', node.label, rhs)

    #--------------------------------------------------

    def visit_MsgSegmark(self, node, children):

        if type(children['depth']) == str:
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
