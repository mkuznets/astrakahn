from collections import defaultdict

from . import lexer as sync_lexer
from . import parser as sync_parser
from .backend import SyncBuilder


def indent(level):
    assert level >= 0
    return '    ' * level


def iprint(level, text):
    if not text:
        print('')
    else:
        print(indent(level) + text)


def compile(code):

    lexer = sync_lexer.build()
    parser = sync_parser.build()

    ast = parser.parse(code, lexer=lexer)

    # -------------------------------------------------------------------------
    # Build intermediate representation.

    tree, vars, actions = SyncBuilder().traverse(ast)

    # -------------------------------------------------------------------------
    # Generate Python code for syncroniser.

    sync_label, *states = tree
    assert sync_label.startswith('sync:')

    sync_name = sync_label.split(':')[1]

    level = 0

    iprint(level, 'from aksync.runtime import *')
    iprint(level, 'from random import sample')
    iprint(level, 'from collections import defaultdict')
    iprint(level, '')

    iprint(level, 'def %s(msgs, orig_state):' % sync_name)
    level += 1

    iprint(level, 'if not msgs: return({}, orig_state.copy())')
    iprint(level, '')

    iprint(level, 'state = orig_state.copy()')
    iprint(level, 'valid_acts = []')
    iprint(level, '')

    # -- state level --
    for st_i, state in enumerate(states):
        state_label, *scopes = state
        assert state_label.startswith('state:')

        state_name = state_label.split(':')[1]

        iprint(level, '%sif state.name == "%s":'
               % ('el' if st_i > 0 else '', state_name))

        level += 1

        # -- scope level --
        for sc_i, scope in enumerate(scopes):

            if sc_i > 0:
                iprint(level, 'if not valid_acts:')
                level += 1

            scope_label, *ports = scope
            assert scope_label.startswith('scope:')

            # -- port level --
            for port in ports:
                port_label, *transitions = port
                assert port_label.startswith('port:')

                port_id = int(port_label.split(':')[1])

                iprint(level, 'if %d in msgs:' % port_id)
                level += 1

                tests = defaultdict(list)

                for pattern_label, trans in transitions:
                    pattern = pattern_label.split(':')[1]
                    tests[pattern].append(trans)

                # -- test level --
                for pattern, predicates in tests.items():
                    if pattern == '__else__':
                        continue

                    iprint(level, 'match, state.locals = %s.test(msgs[%d])' % (pattern, port_id))
                    iprint(level, 'if match:')
                    level += 1

                    for pr_i, (predicate_label, act_id) in enumerate(predicates):
                        predicate = ':'.join(predicate_label.split(':')[1:])
                        iprint(level, '%sif %s.compute(state.vars): '
                               'valid_acts.append((%d, state.locals))'
                               % ('el' if pr_i == 1 else '', predicate, act_id))

                    level -= 1
                # -- test level --

                # -- else level --
                if '__else__' in tests:
                    iprint(level, 'else:')
                    level += 1

                    for i, (predicate_label, act_id) in enumerate(tests['__else__']):
                        predicate = ':'.join(predicate_label.split(':')[1:])
                        iprint(level, '%sif %s.compute(state.vars):'
                               'valid_acts.append((%d, {}))'
                               % ('el' if i == 1 else '', predicate, act_id))

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
        iprint(level, '')
    # -- state level --

    iprint(level, '# --------------')
    iprint(level, '')

    iprint(level, 'if not valid_acts: return({}, orig_state.copy())')
    iprint(level, '')

    iprint(level, 'act_id, state.locals = sample(valid_acts, 1)[0]')
    iprint(level, 'output = defaultdict(list)')
    iprint(level, '')

    for i, (act_id, acts) in enumerate(actions.items()):

        iprint(level, '%sif act_id == %d:' % ('el' if i > 0 else '', act_id))
        level += 1

        for (act_label, *act) in acts:

            if act_label == 'Assign':
                lhs, rhs = act
                iprint(level, 'state.vars["%s"] = %s.compute(state.vars)' % (lhs, rhs))

            if act_label == 'Send':
                msg, port = act
                iprint(level, 'output[%d].append(%s.compute(state.vars))' % (port, msg))

            if act_label == 'Goto':
                name = act[0][0]
                iprint(level, 'state.name = "%s"' % name)

        iprint(level, '')
        level -= 1

    iprint(level, 'state.locals.clear()')
    iprint(level, '')

    iprint(level, 'return(output, state)')
