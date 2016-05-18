from collections import defaultdict
from itertools import chain

from . import lexer as sync_lexer
from . import parser as sync_parser
from .backend import SyncBuilder


def indent(level):
    assert level >= 0
    return '    ' * level


def iprint(level, text):
    if not text:
        return "\n"
    else:
        return indent(level) + text + "\n"


def compile(code):
    asts = compile_to_ast(code)

    output = ''

    for ast in asts:
        output += compile_sync(ast)

    return output


def compile_to_ast(code):
    lexer = sync_lexer.build()
    parser = sync_parser.build()

    asts = parser.parse(code, lexer=lexer)

    return asts


def preamble():
    output = ''
    output += iprint(0, 'from aksync.runtime import *')
    output += iprint(0, 'from random import choice')
    output += iprint(0, 'from collections import defaultdict, ChainMap')
    output += iprint(0, '')

    return output


def compile_sync(ast):
    # Build intermediate representation.

    tree, vars, actions = SyncBuilder(ast).compile()

    # -------------------------------------------------------------------------
    # Generate Python code for syncroniser.

    sync_label, *states = tree
    assert sync_label.startswith('sync:')

    sync_name = sync_label.split(':')[1]

    level = 0
    output = ''

    output += iprint(level, 'class %s:' % sync_name)
    level += 1

    extracts = {}
    ghosts = {}

    output += iprint(level, '@staticmethod')
    output += iprint(level, 'def test(state, msgs, return_locals=False):')
    level += 1

    output += iprint(level, 'if not msgs: return None')
    output += iprint(level, '')

    output += iprint(level, 'valid_acts = []')
    output += iprint(level, '')

    # -- state level --
    for st_i, state in enumerate(states):
        state_label, *scopes = state
        assert state_label.startswith('state:')

        state_name = state_label.split(':')[1]

        output += iprint(level, '%sif state.name == "%s":'
                         % ('el' if st_i > 0 else '', state_name))

        level += 1

        # -- scope level --
        for sc_i, scope in enumerate(scopes):

            if sc_i > 0:
                output += iprint(level, '')
                output += iprint(level, 'if not valid_acts:')
                level += 1

            scope_label, *ports = scope
            assert scope_label.startswith('scope:')

            # -- port level --
            for port in ports:
                port_label, *transitions = port
                assert port_label.startswith('port:')

                port_id = int(port_label.split(':')[1])

                output += iprint(level, 'if msgs.get(%d, None):' % port_id)
                level += 1

                tests = defaultdict(list)

                for _, test, trans in transitions:
                    if test:
                        pattern, tail, depth = test
                        s = (tuple(sorted(pattern)), tail, depth)
                    else:
                        s = None

                    tests[s].append(trans)

                # -- test level --
                for test, predicates in tests.items():

                    if test is None:
                        # else-clause
                        continue

                    pattern, tail, depth = test

                    labels = pattern + (('__n__',) if depth is not None else ())

                    pattern_src = '{%s}' % ', '.join(map(repr, labels))\
                        if labels else 'set()'
                    test_src = '%s <= msgs[%d].keys()' % (pattern_src, port_id)

                    output += iprint(level, 'if %s:' % test_src)
                    level += 1

                    for pr_i, (predicate_label, act_id) in enumerate(
                            predicates):
                        predicate = ':'.join(predicate_label.split(':')[1:])

                        extract_src = '%s._extract(msgs[%d], %d)' % (sync_name,
                                                                     port_id,
                                                                     act_id)

                        # Save test values for lookup table.
                        extracts[act_id] = '[%s], %s, %s' % (
                            ', '.join(map(repr, pattern)),
                            repr(tail),
                            repr(depth)
                        )

                        eval_src = 'eval("%s", state.scope(), local_vars)' % predicate

                        output += iprint(level, 'local_vars = %s' % extract_src)
                        output += iprint(level, 'if %s:' % eval_src)
                        level += 1
                        output += iprint(level, 'valid_acts.append((%d, %d, local_vars))'
                                                % (act_id, port_id))
                        level -= 1

                    level -= 1
                # -- test level --

                # -- else level --
                if None in tests:
                    output += iprint(level, 'else:')
                    level += 1

                    for i, (predicate_label, act_id) in enumerate(tests[None]):
                        predicate = ':'.join(predicate_label.split(':')[1:])

                        eval_src = 'eval("%s", state.scope())' % predicate
                        output += iprint(level, 'if %s:' % eval_src)
                        level += 1
                        output += iprint(level, 'valid_acts.append((%d, %d, {}))'
                                         % (act_id, port_id))
                        level -= 1

                    level -= 1

                level -= 1
                # -- else level --

            # -- port level --

            # Scope
            if sc_i > 0:
                level -= 1
        # -- scope level --

        # State
        level -= 1
        output += iprint(level, '')
    # -- state level --

    output += iprint(level, 'if not valid_acts:')
    level += 1
    output += iprint(level, 'return None')
    level -= 1
    output += iprint(level, '')

    output += iprint(level, 'act_id, port_id, local_vars = choice(valid_acts)')
    output += iprint(level, '')
    output += iprint(level, 'if return_locals: return act_id, port_id, local_vars')
    output += iprint(level, 'else: return act_id, port_id')

    output += iprint(level, '')
    output += iprint(level, '')

    level -= 1
    # --------------------------------------------------------------------------

    output += iprint(level, '@staticmethod')
    output += iprint(level, 'def execute(orig_state, msg, act_id, '
                            'local_vars=None):')
    level += 1

    output += iprint(level, 'state = orig_state.copy()')
    output += iprint(level, 'output = defaultdict(list)')

    output += iprint(level, 'if not local_vars: '
                            'local_vars = %s._extract(msg, act_id)' % sync_name)
    output += iprint(level, 'system = {"ChainMap": ChainMap, "__this__": msg}')
    output += iprint(level, 'scope = dict(ChainMap(state.scope(), system))')

    output += iprint(level, '')

    for i, (act_id, acts) in enumerate(actions.items()):

        output += iprint(level,
                         '%sif act_id == %d:' % ('el' if i > 0 else '', act_id))
        level += 1

        if not acts:
            output += iprint(level, 'pass')

        else:
            for (act_label, *act) in acts:

                if act_label == 'Assign':
                    lhs, rhs = act
                    output += iprint(level, 'local_vars["%s"] = eval(%s, '
                                            'scope, local_vars)' % (lhs,
                                                                    repr(rhs)))

                if act_label == 'Send':
                    msg, port = act
                    output += iprint(level, 'output[%d].append(' % port)
                    output += iprint(level, '   eval(%s, scope, '
                                            'local_vars)' % repr(msg))
                    output += iprint(level, ')')

                if act_label == 'Goto':
                    state = act[0]
                    output += iprint(level, 'state.name = "%s"' % state)

        output += iprint(level, 'state.update(local_vars)')
        output += iprint(level, '')
        level -= 1

    output += iprint(level, '')

    output += iprint(level, 'return output, state')
    level -= 1
    output += iprint(level, '')

    # --------------------------------------------------------------------------

    output += iprint(level, '@staticmethod')
    output += iprint(level, 'def init():')
    level += 1
    output += iprint(level,
                     'return State(name="start", %s)' % (", ".join(vars)))
    level -= 1
    output += iprint(level, '')

    # --------------------------------------------------------------------------

    output += iprint(level, '@staticmethod')
    output += iprint(level, 'def _extract(msg, act_id):')
    level += 1

    output += iprint(level, 'args = {')
    for act_id, args in extracts.items():
        output += iprint(level+1, '%d: (%s),' % (act_id, args))
    output += iprint(level, '}')

    output += iprint(level, 't = args[act_id]')
    output += iprint(level, 'return extract(msg, *t)')

    level -= 1
    output += iprint(0, '')

    # --------------------------------------------------------------------------

    output += iprint(level, '@staticmethod')
    output += iprint(level, 'def run(state, msgs):')
    level += 1

    output += iprint(level, 'test = %s.test(state, msgs, True)' % sync_name)
    output += iprint(level, 'if test:')
    level += 1

    output += iprint(level, 'act_id, port_id, local_vars = test')
    output += iprint(level, 'output, state = %s.execute(state, '
                            'msgs[port_id], act_id, local_vars)' % sync_name)

    output += iprint(level, 'return(output, state, (port_id,))')

    level -= 1
    output += iprint(level, 'else: return {}, state, None')
    output += iprint(level, '')

    # --------------------------------------------------------------------------

    return output
