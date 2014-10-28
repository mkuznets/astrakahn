#!/usr/bin/env python3

import communication as comm
import components

import collections


class Sync(components.Vertex):

    def __init__(self, decls, states):

        # Mapping from channel names to port ids.
        self.input_index = {p['name']: i for i, p in enumerate(self.inputs)}
        self.output_index = {p['name']: i for i, p in enumerate(self.outputs)}

        self.this = {'channel': None, 'msg': None}
        self.variables = {}
        self.aliases = {}

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
            for channel, handler in state.handlers.items():
                for trans in handler.transitions:
                    trans.init_data(self.this, self.variables, self.variables)

    @property
    def channel_handler(self):
        if self.this['channel'] in self.state:
            return self.state[self.this['channel']]
        else:
            return None

    @property
    def state(self):
        return self.states[self.state_name]

    @property
    def outputs_blocked(self):

        blocked = []

        for i, port in enumerate(self.n_outputs):
            if port['to'] is None or not port['to'].is_space_for(1):
                blocked.append(i)

        return blocked

    #################################

    def is_ready(self):

        # Inputs with messages available
        inputs_available = self.inputs_available()

        # Inputs that can cause transitions from the current state
        inputs_feasible = set(inputs_available) & set(self.state.inputs())

        if len(inputs_feasible) == 0:
            # No transitions for available messages
            return (False, False)

        # Inputs that cause transitions either with `send's to available
        # channels or without `send's at all.
        inputs_ready = set()

        for channel in inputs_feasible:

            # Outputs to which messages can be sent providing fetching
            # a message from `channel'.
            outputs_impacted = self.state[channel].impact()

            if not outputs_impacted & self.outputs_blocked:
                inputs_ready.add(channel)

        if len(inputs_ready) == 0:
            # No transitions that can be taken immediately.
            return (True, False)

        self.inputs_ready = inputs_ready
        return (True, True)

    def fetch(self):

        # Mapping from inputs to number of accepted messages.
        stats = {c: self.state[c].counter for c in self.inputs_ready}

        # Choose least frequently taken channel.
        channel = min(stats, key=stats.get)

        # Get a message from selected channel.
        self.this['msg'] = channel.get()
        self.this['channel'] = channel

        # Increment usage counter on the chosen handler.
        self.channel_handler.mark_use()

    def run(self):

        transition = self.channel_handler.choose_transition()
        transition.mark_use()

        # 1. Assign
        transition.assign()

        # 2. Send
        output = transition.send()
        self.send_out(output, wrap=True)

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
            for state_name in states:
                state = self.states[state_name]

                if self.input_available(state.inputs()) \
                        and self.output_available(state.impact()):
                    immediate.append(state_name)

        # Choose less frequently taken state from either immediately available
        # or the whole set of states.
        stats = {s: self.states[s].counter
                 for s in (immediate if immediate else states)}
        state_name = min(stats, key=stats.get)

        return state_name

    #------ Construction methods --------------

    def add_state(self):
        pass

    def add_transition(self):
        pass

    #-------------------------------------------


class SyncState:

    def __init__(self, handlers):

        self.name = ''
        self.handlers = {h.channel_name: h for h in handlers}

    def inputs(self):
        return self.handlers.keys()

    def impact(self):
        outputs_impacted = set()

        for channel, handler in self.handlers.items():
            outputs_impacted |= handler.impact()

        return outputs_impacted

    def __getitem__(self, channel):
        return self.handlers[channel]

    def __contains__(self, channel):
        return channel in self.handlers


class SyncChannelHandler:

    def __init__(self, transitions):

        self.channel_name = None
        self.counter = 0

        self.transitions = transitions

    def impact(self):
        '''
        Collect outputs to which messages can be sent while performing
        transition from the group.
        '''
        outputs_impacted = set()

        for trans in self.transitions:
            outputs_impacted |= trans.impact()

        return outputs_impacted

    def mark_use(self):
        self.counter += 1

    def choose_transition(self):
        '''
        Choose transitions that satisfy conditions and select the least
        frequently taken one.
        '''

        scopes = {}

        # Group transition by scopes.
        for trans in self.transitions:
            scopes[trans.scope] = scopes.get(trans.scope, []) + [trans]

        for i in sorted(scopes.keys()):
            scope = scopes[i]

            # Collect valid transitions.
            #
            for trans in scope:
                valid_trans = []
                fallback = None

                if trans.is_fallback() and trans.test():
                    # .else condition.
                    fallback = trans
                    continue
                elif trans.test():
                    # test condition.
                    valid_trans.append(trans)

            # Select transition from the list of valid ones.
            #
            if not (valid_trans or fallback):
                # No transition available, go to next scope.
                continue

            elif not valid_trans and fallback:
                # Pick .else transition if nothing else available.
                return fallback

            elif valid_trans:
                stats = {t.counter: t for t in valid_trans}
                trans = min(stats, stats.get)
                return trans

        # No available transitions: do nothing (go to the same state).
        return None


class SyncTransition:

    def __init__(self):

        self.channel = None
        self.scope = None

        self.condition = None  # <simple stmt>
        self.guard = None  # <simple stmt>

        self.assign = []
        self.send = []
        self.goto = []

        # References to the sync's data structures
        self.this = None
        self.variables = None
        self.aliases = None

        # Aliases from the condition test. If the transition is taken, they
        # will be copied to state.
        self.aliases_local = {}

        self.counter = 0

    def init_data(this, variables, aliases):
        self.this = this
        self.variables = variables
        self.aliases = aliases

    def test(self):
        self.aliases_local.clear()

        if self.test_condition() and self.test_guard():
            return True
        else:
            self.aliases_local.clear()
            return False

    def test_condition(self):
        msg = self.this['msg']

        if self.condition is None:
            return True

        cond_type = self.condition[0]

        # on C.@depth
        if cond_type == 'segmark':
            name = self.condition[1]

            if isinstance(msg, comm.SegmentationMark):
                self.aliases_local[name] = msg.n
                return True
            else:
                return False

        # on C.?variant
        elif cond_type == 'choice':
            variant = self.condition[1]
            if isinstance(msg, comm.DataMessage) and msg.variant == variant:
                return True
            else:
                return False

        # on C.(id, id || id_tail)
        elif cond_type == 'pattern':
            pattern, tail = self.condition[1]

            if isinstance(msg, comm.Record) and pattern in msg:
                self.aliases_local.update(msg.extract(pattern, tail))
                return True
            else:
                return False

        # on C.?variant(id, id || id_tail)
        elif cond_type == 'choice_pattern':
            variant = self.condition[1]
            pattern, tail = self.condition[2]

            if isinstance(msg, comm.Record) and msg.variant == variant and pattern in msg:
                self.aliases_local.update(msg.extract(pattern, tail))
                return True
            else:
                return False

    def test_guard(self):

        if self.guard is None:
            return True

        # Guard must be a lambda expression.
        assert(callable(self.guard))

        scope = self.state_vars.copy()
        scope.update(self.aliases_local)

        # Collect argument values from the scope.
        args = (scope[n] for n in self.guard.__code__.co_varnames)

        # Execute guard expression.
        return True if bool(self.guard(*args)) else False

    def assign(self):

        for stmt in self.assign:
            lhs, exp = stmt

            if callable(exp):
                pass
                # State variable
            else:
                pass
                # Store variable

    def send(self):
        pass

    def goto(self):
        return self.goto

    def impact(self):
        '''
        Get outputs to which messages can be sent while performing
        the transition.
        '''
        return set(stmt[0] for stmt in self.send)

    def mark_use(self):
        # Move local aliases to the transition scope.
        self.aliases.update(self.aliases_local)
        self.counter += 1


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

    def __repr__(self):
        return 'StateInt({})'.format(self.width)


class StoreVar(Variable):

    def __init__(self, name, channel):
        super(StoreVar, self).__init__(name)
        self.channel = channel

    def set(self, value):
        self.value = value

    def __repr__(self):
        return 'StoreVar({})'.format(self.channel)
