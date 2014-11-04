#!/usr/bin/env python3

import communication as comm
from . import abstract


class Sync(abstract.Vertex):

    def __init__(self, name, inputs, outputs, scope, states):

        super(Sync, self).__init__(name, inputs, outputs)

        self.this = {'port': None, 'msg': None}
        self.states = {s.name: s for s in states}
        self.scope = scope

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
                    trans.init_data(self.this, self.scope)

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

        if transition is None:
            return

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

        # Clean up
        self.scope.clear_tmp()

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

            valid_trans = []
            else_trans = None

            # Collect valid transitions.
            #
            for trans in order:

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

        # References to the sync's data structures
        self.this = None

        self.local_aliases = {}

        # Order is set externally.
        self.order = -1
        self.hits = 0

    #---------------------------------------------------

    def init_data(self, this, scope):
        self.this = this
        self.scope = scope

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
        self.scope.add_from(self.local_aliases)

    #---------------------------------------------------

    def test(self):
        result = self.test_condition() and self.test_guard()
        self.scope.clear_tmp()
        return result

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
            self.scope[depth] = msg.n

            return True

        # on C.?variant
        elif ctype == 'CondDataMsg':

            if not isinstance(msg, comm.Record):
                return False

            alt, pattern, tail = self.condition[1:]

            if alt and msg.alt != alt:
                return False

            if pattern or tail:
                if not isinstance(msg, comm.Record) or (pattern not in msg):
                    return False
                self.local_aliases = msg.extract(pattern, tail)
                self.scope.add_from(self.local_aliases)

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

            self.scope[lhs] = result

    def send(self):

        dispatch = {}

        for act in self.actions['Send']:
            msg, port = act[1:]
            mtype = msg[0]

            if mtype == 'MsgSegmark':
                dtype, depth = msg[1]

                if dtype == 'DepthVar':
                    assert(depth in self.scope
                           and type(self.scope[depth]) == int)

                    outcome = comm.SegmentationMark(self.scope[depth])

                elif dtype == 'IntExp':
                    result = self._compute_intexp(depth)
                    outcome = comm.SegmentationMark(result)

                else:
                    raise AssertionError('Unsupported type of segmark depth.')
                    return

            elif mtype == 'MsgData':
                alt, dataexp = msg[1:]

                content = self._compute_dataexp(dataexp[1])
                outcome = comm.Record(content)

                if alt:
                    outcome.alt = alt

            elif mtype == 'MsgNil':
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

    def _compute_intexp(self, exp):

        assert(callable(exp))

        # Collect argument values from the scope.
        args = (self.scope[n] for n in exp.__code__.co_varnames)

        # Evaluate expression.
        return int(exp(*args))

    def _compute_dataexp(self, items):

        content = {}

        for item in items:

            if item[0] == 'ItemThis':
                assert(isinstance(self.this['msg'], comm.Record))
                new_item = self.this['msg'].content

            elif item[0] == 'ItemVar':
                var = item[1]
                assert(var in self.scope
                       and type(self.scope[var]) == dict)
                new_item = self.scope[var]

            elif item[0] == 'ItemPair':

                label, rhs = item[1:]

                if rhs[0] == 'ID':
                    assert(rhs[1] in self.scope)
                    new_item = {label: self.scope[rhs[1]]}

                elif rhs[0] == 'IntExp':
                    result = self._compute_intexp(rhs[1])
                    new_item = {label: result}

                else:
                    raise AssertionError('Unsupported type of '
                                         'rhs: {}'.format(rhs[0]))
                    return

            else:
                raise AssertionError('Unsupported type of '
                                     'expression: {}'.format(item[0]))
                return

            content.update(new_item)

        return content

#------------------------------------------------------------------------------


class Scope:

    def __init__(self, items):
        self.items = []
        self.tmp_items = []

        self.index = {}

        for v in items:
            if not isinstance(v, Variable):
                raise ValueError('Item of a wrong type: {}'.format(type(v)))
            else:
                self.items.append(v)
                self.index[v.name] = v

    def clear_tmp(self):
        for v in self.tmp_items:
            del self.index[v.name]
        del self.tmp_items[:]

    def __getitem__(self, name):
        if name in self.index:
            return self.index[name].get()
        else:
            raise IndexError('Name `{}\' is not in the scope'.format(name))

    def __setitem__(self, name, value):
        if name in self.index:
            # Set value to existing variable.
            self.index[name].set(value)
        else:
            # Create new temporary variable.
            obj = Alias(name)
            obj.set(value)
            self.tmp_items.append(obj)
            self.index[name] = obj

    def add_from(self, container):
        if not isinstance(container, dict):
            raise ValueError('add_from() supports only dict containers.')
        else:
            for n, v in container.items():
                self.__setitem__(n, v)

    def __contains__(self, name):
        return name in self.index

#------------------------------------------------------------------------------


class Variable:

    def __init__(self, name):
        self.name = name
        self.value = None

    def get(self):
        return self.value

    def set(self, value):
        raise NotImplemented('Set method not implemented for abstract type.')


class Alias(Variable):

    def __init__(self, name):
        super(Alias, self).__init__(name)
        self.value = 0

    def set(self, value):
        self.value = value

    def __int__(self):
        return self.value

    def __repr__(self):
        return 'Alias({})'.format(self.name)


class Const(Variable):

    def __init__(self, name, value):
        super(Const, self).__init__(name)
        self.value = value

    def set(self, value):
        raise AssertionError('Constant cannot be changed.')

    def __int__(self):
        return self.value

    def __repr__(self):
        return 'Const({}={})'.format(self.name, self.value)


class StateInt(Variable):

    def __init__(self, name, width):
        super(StateInt, self).__init__(name)
        self.width = width
        self.value = 0

    def set(self, value):
        if value >= 0 and value <= 2 ** self.width:
            self.value = value
        else:
            raise RuntimeError('Value is out of range.')

    def __int__(self):
        return self.value

    def __repr__(self):
        return 'StateInt({})'.format(self.width)


class StateEnum(Variable):

    def __init__(self, name, labels):
        super(StateEnum, self).__init__(name)
        self.labels = tuple(labels)
        self.label_map = {n: i for i, n in enumerate(labels)}
        self.value = 0

    def set(self, value):

        if type(value) == str:
            # Set named constant.
            if value in self.label_map:
                self.value = self.label_map[value]
            else:
                raise IndexError('Label {} is not defined '
                                 'for the enum'.format(value))

        elif type(value) == int:
            # Set integer value.
            # NOTE: It is not checked that the given number is in the range of
            # declared named constants. In this sence StateEnum is equivalent
            # to StateInt.
            self.value = value

    def __int__(self):
        return self.value

    def __repr__(self):
        return 'StateEnum({}, {})'.format(self.name, self.labels)


class StoreVar(Variable):

    def __init__(self, name):
        super(StoreVar, self).__init__(name)
        self.value = {}

    def set(self, value):
        self.value = value

    def __repr__(self):
        return 'StoreVar({})'.format(self.name)
