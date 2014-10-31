#!/usr/bin/env python3

import communication as comm
import components


class Sync(components.Vertex):

    def __init__(self, name, inputs, outputs, decls, states):

        super(Sync, self).__init__(name, inputs, outputs)

        self.this = {'port': None, 'msg': None}

        self.decls = {v.name: v for v in decls}
        self.states = {s.name: s for s in states}

        # Initial state
        self.state_name = 'start'

        # Compiler must guarantee the presence of the inital state.
        assert(self.state_name in self.states)

        # Inputs from which messages can be fetched at the current
        # state (the result of .is_ready() execution).
        self.inputs_ready = None

        # Initiate transition with variables.
        for name, state in self.states.items():
            for port, handler in state.handlers.items():
                for trans in handler.transitions:
                    trans.init_data(self.this, self.decls)

    #---------------------------------------------------

    @property
    def port_handler(self):
        if self.this['port'] in self.state:
            return self.state[self.this['port']]
        else:
            return None

    @property
    def state(self):
        return self.states[self.state_name]

    #---------------------------------------------------

    def inputs_available(self):
        port_list = []

        for i, p in enumerate(self.inputs):
            if not p['queue'].is_empty():
                port_list.append(i)

        return port_list

    def outputs_blocked(self):

        blocked = set()

        for i, port in enumerate(self.outputs):
            if port['to'] is None or not port['to'].is_space_for(1):
                blocked.add(i)

        return blocked

    #---------------------------------------------------

    def is_ready(self):

        # Inputs with messages available
        inputs_available = self.inputs_available()

        # Inputs that can cause transitions from the current state
        inputs_feasible = set(inputs_available) & set(self.state.inputs())

        if not inputs_feasible:
            # No transitions for available messages
            return (False, False)

        # Inputs that cause transitions either with `send's to available
        # ports or without `send's at all.
        inputs_ready = set()

        for port in inputs_feasible:

            # Outputs to which messages can be sent providing fetching
            # a message from `port'.
            outputs_impacted = self.state[port].impact()

            if not outputs_impacted & self.outputs_blocked():
                inputs_ready.add(port)

        if len(inputs_ready) == 0:
            # No transitions that can be taken immediately.
            return (True, False)

        self.inputs_ready = inputs_ready
        return (True, True)

    def fetch(self):

        # Mapping from inputs to number of accepted messages.
        stats = {c: self.state[c].hits for c in self.inputs_ready}

        # Choose least frequently taken port.
        port = min(stats, key=stats.get)

        # Get a message from selected port.
        self.this['msg'] = self.get(port)
        self.this['port'] = port

        # Increment usage counter on the chosen handler.
        self.port_handler.hit()

        self.run()

    def run(self):

        transition = self.port_handler.choose_transition()
        transition.hit()

        # 1. Assign
        transition.assign()

        # 2. Send
        dispatch = transition.send()
        self.send_out(dispatch)

        # 3. Goto
        goto_states = transition.goto()

        if goto_states:
            self.state_name = self.choose_state(goto_states)
        else:
            # Do nothing if `goto' statement is not specified.
            pass

    def choose_state(self, states):
        '''
        Choose the most preferable state to move among the given ones.
        '''

        immediate = []

        if len(states) == 1:
            return states[0]

        else:
            # TODO: not tested
            for state_name in states:
                state = self.states[state_name]

                if self.input_available(state.inputs()) \
                        and self.output_available(state.impact()):
                    immediate.append(state_name)

        # Choose less frequently taken state from either immediately available
        # or the whole set of states.
        stats = {s: self.states[s].hits
                 for s in (immediate if immediate else states)}
        state_name = min(stats, key=stats.get)

        return state_name


class State:

    def __init__(self, name, handler_list):
        self.name = name
        self.handlers = {h.port: h for h in handler_list}

    def inputs(self):
        return set(self.handlers.keys())

    def impact(self):
        outputs_impacted = set()

        for port, handler in self.handlers.items():
            outputs_impacted |= handler.impact()

        return outputs_impacted

    def __getitem__(self, port):
        return self.handlers[port]

    def __contains__(self, port):
        return port in self.handlers


class PortHandler:

    def __init__(self, port, transitions):
        self.port = port
        self.transitions = transitions

        self.hits = 0

    def impact(self):
        '''
        Collect outputs to which messages can be sent while performing
        transition from the group.
        '''
        outputs_impacted = set()

        for trans in self.transitions:
            outputs_impacted |= trans.impact()

        return outputs_impacted

    def hit(self):
        self.hits += 1

    def choose_transition(self):
        '''
        Choose transitions that satisfy conditions and select the least
        frequently taken one.
        '''
        orders = {}

        for trans in self.transitions:
            orders[trans.order] = orders.get(trans.order, []) + [trans]

        for i in sorted(orders.keys()):
            order = orders[i]

            # Collect valid transitions.
            #
            for trans in order:
                valid_trans = []
                else_trans = None

                if trans.is_else() and trans.test():
                    # .else condition.
                    else_trans = trans
                    continue

                elif trans.test():
                    # test condition.
                    valid_trans.append(trans)

            # Select transition from the list of valid ones.
            #
            if not (valid_trans or else_trans):
                # No transition available, go to next order.
                continue

            elif not valid_trans and else_trans:
                # Pick .else transition if nothing else available.
                return else_trans

            elif valid_trans:
                # One or more transitions are valie: choose the least
                # frequently taken one.
                stats = {t: t.hits for t in valid_trans}
                trans = min(stats, key=stats.get)
                return trans

        # No transitions available.
        return None


class Transition:

    def __init__(self, port, condition, guard, actions):

        assert(condition and guard)

        self.port = port
        self.condition = condition
        self.guard = guard

        self.actions = {'Goto': [], 'Assign': [], 'Send': []}
        # Group actions by type.
        for act in actions:
            self.actions[act[0]].append(act)

        self.aliases = {}

        # References to the sync's data structures
        self.this = None
        self.decls = None

        # Order is set externally.
        self.order = -1
        self.hits = 0

    #---------------------------------------------------

    def init_data(self, this, decls):
        self.this = this
        self.decls = decls

    #---------------------------------------------------

    def is_else(self):
        return self.condition[0] == 'CondElse'

    def impact(self):
        '''
        Get outputs to which messages can be sent while performing
        the transition.
        '''
        return set(act[2] for act in self.actions if act[0] == 'Send')

    def hit(self):
        self.hits += 1

    #---------------------------------------------------

    def test(self):
        self.aliases.clear()

        if self.test_condition() and self.test_guard():
            return True
        else:
            self.aliases.clear()
            return False

    def test_condition(self):
        msg = self.this['msg']

        ctype = self.condition[0]

        # on C
        # on C.else
        if ctype == 'CondElse' or ctype == 'CondEmpty':
            return True

        # on C.@depth
        elif ctype == 'CondSegmark':

            if not isinstance(msg, comm.SegmentationMark):
                return False

            depth = self.condition[1]
            self.aliases[depth] = msg.n

            return True

        # on C.?variant
        elif ctype == 'CondDataMsg':

            if not isinstance(msg, comm.DataMessage):
                return False

            alt, pattern, tail = self.condition[1:]

            if alt and msg.alt != alt:
                return False

            if pattern or tail:
                if not isinstance(msg, comm.Record) or (pattern not in msg):
                    return False
                self.aliases.update(msg.extract(pattern, tail))

            return True

    def test_guard(self):

        if not self.guard:
            return True

        assert(self.guard[0] == 'IntExp')

        exp = self.guard[1]
        result = self._compute_intexp(exp)

        return bool(result)

    #---------------------------------------------------

    def assign(self):

        for act in self.actions['Assign']:
            lhs, rhs = act[1:]
            type, content = rhs

            if type == 'DataExp':
                result = self._compute_dataexp(content)

            elif type == 'IntExp':
                result = self._compute_intexp(content)

            else:
                raise AssertionError('Unsupported type of expression')
                return

            if lhs in self.decls:
                self.decls[lhs] = result
            else:
                self.aliases[lhs] = result

    def send(self):

        dispatch = {}

        for act in self.actions['Send']:
            msg, port = act[1:]
            type = msg[0]

            if type == 'MsgSegmark':
                dtype, depth = msg[1]

                if dtype == 'DepthVar':
                    scope = self._var_scope()
                    assert(depth in scope and type(scope[depth]) == int)
                    outcome = comm.SegmentationMark(scope[depth])

                elif dtype == 'IntExp':
                    result = self._compute_intexp(depth)
                    outcome = comm.SegmentationMark(result)

                else:
                    raise AssertionError('Unsupported type of segmark depth.')
                    return

            elif type == 'MsgData':
                alt, dataexp = msg[1:]

                outcome = self._compute_dataexp(dataexp[1])

                if alt:
                    outcome.alt = alt

            elif type == 'MsgNil':
                outcome = comm.NilMessage()

            dispatch.update({port: outcome})

        return dispatch

    def goto(self):
        goto_acts = self.actions['Goto']

        if not goto_acts:
            return None

        act = goto_acts[0]
        return act[1]

    #---------------------------------------------------

    def _var_scope(self):
        scope = self.decls.copy()
        scope.update(self.aliases)
        return scope

    def _compute_intexp(self, exp):

        assert(callable(exp))

        scope = self._var_scope()
        # Collect argument values from the scope.
        args = (scope[n] for n in exp.__code__.co_varnames)

        # Evaluate expression.
        return int(exp(*args))

    def _compute_dataexp(self, items):

        content = {}

        scope = self._var_scope()

        for item in items:

            if item[0] == 'ItemThis':
                assert(isinstance(self.this['msg'], comm.Record))
                new_item = self.this['msg'].content

            elif item[0] == 'ItemVar':
                var = item[1]
                assert(var in scope and isinstance(scope[var], comm.Record))
                new_item = scope[var].content

            elif item[0] == 'ItemPair':
                label, var = item[1:]
                assert(var in scope)
                new_item = {label: scope[var].content}

            else:
                raise AssertionError('Unsupported type of expression')
                return

            content.update(new_item)

        return comm.Record(content)

#------------------------------------------------------------------------------


class Variable:

    def __init__(self, name):
        self.name = name
        self.value = None

    def get(self):
        return self.value

    def set(self):
        raise NotImplemented('Set method not implemented for abstract type.')


class StateInt(Variable):

    def __init__(self, name, width):
        super(StateInt, self).__init__(name)
        self.width = width
        self.value = 0

    def set(self, value):
        if value > 0 and value <= 2 ** self.width:
            self.value = value
        else:
            raise RuntimeError('Value is out of range.')

    def __int__(self):
        return self.value

    def __repr__(self):
        return 'StateInt({})'.format(self.width)


class StateEnum(Variable):

    def __init__(self, name, labels):
        super(StateInt, self).__init__(name)
        self.labels = tuple(labels)
        self.label_map = {n: i for i, n in enumerate(labels)}
        self.value = 0

    def set(self, label):
        if label in self.label_map:
            self.value = self.label_map[label]
        else:
            raise ValueError('Label {} is not defined '
                             'for the enum'.format(label))

    def get(self, label):
        return self.labels[self.value]

    def __int__(self):
        return self.value

    def __repr__(self):
        return 'StateInt({}, {})'.format(self.name, self.width)


class StoreVar(Variable):

    def __init__(self, name):
        super(StoreVar, self).__init__(name)

    def set(self, value):
        self.value = value

    def __repr__(self):
        return 'StoreVar({})'.format(self.name)
