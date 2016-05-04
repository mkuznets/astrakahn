from collections import defaultdict

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
    output = ''

    output += iprint(level, 'from aksync.runtime import *')
    output += iprint(level, 'from random import sample')
    output += iprint(level, 'from collections import defaultdict, ChainMap')
    output += iprint(level, '')

    output += iprint(level, 'def %s(msgs, orig_state):' % sync_name)
    level += 1

    output += iprint(level, 'if not msgs: return({}, orig_state.copy(), ())')
    output += iprint(level, '')

    output += iprint(level, 'state = orig_state.copy()')
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

                for pattern_label, trans in transitions:
                    pattern = pattern_label.split(':')[1]
                    tests[pattern].append(trans)

                # -- test level --
                for pattern, predicates in tests.items():
                    if pattern == '__else__':
                        continue

                    output += iprint(level,
                                     'match, state.locals = %s.test(msgs[%d])'
                                     % (pattern, port_id)
                    )
                    output += iprint(level, 'if match:')
                    level += 1

                    for pr_i, (predicate_label, act_id) in enumerate(predicates):
                        predicate = ':'.join(predicate_label.split(':')[1:])
                        output += iprint(
                            level, '%sif (%s): '
                            'valid_acts.append((%d, %d, state.locals))'
                            % ('el' if pr_i == 1 else '', predicate, act_id, port_id)
                        )

                    level -= 1
                # -- test level --

                # -- else level --
                if '__else__' in tests:
                    output += iprint(level, 'else:')
                    level += 1

                    for i, (predicate_label, act_id) in enumerate(tests['__else__']):
                        predicate = ':'.join(predicate_label.split(':')[1:])
                        output += iprint(level, '%sif (%s): '
                               'valid_acts.append((%d, %d, {}))'
                               % ('el' if i == 1 else '', predicate, act_id, port_id))

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

    output += iprint(level, '# --------------')
    output += iprint(level, '')

    output += iprint(level, 'if not valid_acts: return({}, orig_state.copy(), ())')
    output += iprint(level, '')

    output += iprint(level, 'act_id, port_id, state.locals = '
                            'sample(valid_acts, 1)[0]')

    output += iprint(level, 'output = defaultdict(list)')
    output += iprint(level, 'msg = msgs[port_id]')
    output += iprint(level, '')

    for i, (act_id, acts) in enumerate(actions.items()):

        output += iprint(level, '%sif act_id == %d:' % ('el' if i > 0 else '', act_id))
        level += 1

        if not acts:
            output += iprint(level, 'pass')

        else:
            for (act_label, *act) in acts:

                if act_label == 'Assign':
                    lhs, rhs = act
                    output += iprint(level, 'state["%s"] = %s' % (lhs, rhs))

                if act_label == 'Send':
                    msg, port = act
                    output += iprint(level, 'output[%d].append(%s)' % (port, msg))

                if act_label == 'Goto':
                    states = act[0]
                    name = states[0]
                    output += iprint(level, 'state.name = "%s"' % name)

        output += iprint(level, '')
        level -= 1

    output += iprint(level, 'state.locals.clear()')
    output += iprint(level, '')

    output += iprint(level, 'return(output, state, (port_id,))')
    level -= 1
    output += iprint(level, '')

    output += iprint(level, 'def %s_init():' % sync_name)
    level += 1
    output += iprint(level, 'return State(name="start", %s)' % (", ".join(vars)))
    level -= 1

    return output
