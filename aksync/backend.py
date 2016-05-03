#!/usr/bin/env python3

from collections import defaultdict

from . import ast


class SyncBuilder(ast.NodeVisitor):

    def __init__(self):

        self._actions = {}
        self._actions_key = 0

        # Mapping from port names to port ids.
        self.input_index = None
        self.output_index = None

    def add_actions(self, actions):
        t = self._actions_key
        self._actions_key += 1

        self._actions[t] = actions
        return t

    def visit_Sync(self, node, ch):  # -> [tree, vars, actions]
        return ('sync:%s' % node.name.value, *ch['states']), ch['decls'], self._actions

    # --------------------------------------------------

    def visit_PortList(self, node, ch):

        index = {n: i for i, n in enumerate(ch['ports'])}

        if self.input_index is None:
            self.input_index = index
        else:
            self.output_index = index

        return ch['ports']

    def visit_Port(self, node, ch):
        return ch['name']

    def visit_DepthExp(self, node, ch):
        raise NotImplementedError('Channel depth')

    def visit_DepthNone(self, node, _):
        pass

    # --------------------------------------------------

    def visit_DeclList(self, node, ch):
        return ch['decls']

    def visit_StoreVar(self, node, ch):
        return 'store:%s' % ch['name']

    def visit_StateVar(self, node, ch):
        return 'state:%s' % ch['name']

    def visit_IntType(self, node, ch):
        return ('int', ch['size'])

    def visit_StateList(self, node, ch):
        return ch['states']

    def visit_State(self, node, ch):

        scopes = []

        for i, order in enumerate(ch['trans_orders']):

            byport = defaultdict(list)
            for trans in order:
                byport[trans[0]] += [trans[1]]

            scopes.append(
                ('scope:%d' % i, *((p, *t) for p, t in byport.items()))
            )

        state = ('state:%s' % ch['name'], *scopes)

        return state

    def visit_TransOrder(self, node, ch):
        return ch['trans_stmt']

    def visit_Trans(self, node, ch):
        pid = self.input_index[ch['port']]

        act_id = self.add_actions(ch['actions'])

        return ('port:%d' % pid,
                ('pattern:%s' % ch['condition'],
                 ('predicate:%s' % ch['guard'], act_id)))

    # --------------------------------------------------

    def visit_CondSegmark(self, node, ch):
        return 'ConditionSegmark(%s, [%s], %s)' % \
            (ch['depth'],
             ', '.join(ch['pattern']),
             ch['tail'])

    def visit_CondChoice(self, node, ch):
        return 'ConditionData([%s], %s)' % \
            (', '.join('"%s"' % l for l in ch['pattern']),
             ch['tail'])

    def visit_CondDataMsg(self, node, ch):
        return 'ConditionData([%s], %s)' % \
            (', '.join('"%s"' % l for l in ch['pattern']),
             ch['tail'])

    def visit_CondEmpty(self, node, _):
        return 'ConditionPass()'

    def visit_CondElse(self, node, _):
        return '__else__'

    # --------------------------------------------------

    def visit_Assign(self, node, ch):
        return ('Assign', ch['lhs'], ch['rhs'])

    def visit_Send(self, node, ch):
        pid = self.output_index[ch['port']]
        return ('Send', ch['msg'], pid)

    def visit_Goto(self, node, ch):
        return ('Goto', ch['states'])

    # --------------------------------------------------

    def visit_DataExp(self, node, ch):
        terms = ch['terms']

        if not terms:
            return []
        else:
            terms.reverse()
            return ', '.join(terms)

    def visit_ItemThis(self, node, _):
        return 'msg'

    def visit_ItemVar(self, node, ch):
        return 'state["%s"]' % (ch['name'])

    def visit_ItemExpand(self, node, ch):
        return '{"%s": state["%s"]}' % (ch['name'], ch['name'])

    def visit_ItemPair(self, node, ch):
        return '{"%s": %s}' % (ch['label'], ch['value'])

    # --------------------------------------------------

    def visit_MsgSegmark(self, node, ch):
        if not ch['data_exp']:
            return '{"__n__": %s}' % ch['depth']
        else:
            return 'dict(ChainMap({"__n__": %s}, %s))' % (ch['depth'],
                                                          ch['data_exp'])

    def visit_MsgRecord(self, node, ch):
        if not ch['data_exp']:
            return '{}'
        else:
            return 'dict(ChainMap(%s))' % ch['data_exp']

    # --------------------------------------------------

    def visit_IntExp(self, node, _):

        values = {key: term.value for key, term in node.terms.items()}
        # print(values)
        # args = [term for term in values.values() if type(term) is str]
        #
        # code = 'lambda %s: %s' % (', '.join(set(args)),
        #                           node.exp.format(**values))

        return node.exp.format(**{k: 'state["%s"]' % v if type(v) is str else v
                                  for k,v in values.items()})

    def visit_ID(self, node, _):
        return node.value

    def visit_TERM(self, node, _):
        return node.value

    def visit_NUMBER(self, node, _):
        return node.value

    # --------------------------------------------------

    def generic_visit(self, node, _):
        print('GV:', node)
