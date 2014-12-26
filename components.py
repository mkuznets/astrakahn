#!/usr/bin/env python3

import sys
import communication as comm


class Node:
    def __init__(self, name, inputs, outputs):
        self._id = None
        self.name = name

        self.ast = None
        self.cores = None
        self.path = None

        # Ports of the node itselt
        self.inputs = [{'id': i, 'vid': self.id, 'name': n, 'queue': None, 'src': None}
                       for i, n in enumerate(inputs)]
        self.outputs = [{'id': i, 'vid': self.id, 'name': n, 'to': None, 'dst': None}
                        for i, n in enumerate(outputs)]

    # DIRTY FUCKING HACK
    def fix_port_id(self):
        for i, p in enumerate(self.inputs):
            p['id'] = i
        for i, p in enumerate(self.outputs):
            p['id'] = i

    @property
    def id(self):
        return self._id

    # DIRTY FUCKING HACK
    @id.setter
    def id(self, value):
        self._id = value
        for i, p in enumerate(self.inputs):
            p['vid'] = value
        for i, p in enumerate(self.outputs):
            p['vid'] = value


    @property
    def n_inputs(self):
        return len(self.inputs)

    @property
    def n_outputs(self):
        return len(self.outputs)

    def free_ports(self):
        inputs = {}
        outputs = {}

        for p in self.inputs:
            name = p['name']
            if p['src'] is None:
                inputs[name] = inputs.get(name, []) + [(self.id, p)]

        for p in self.outputs:
            name = p['name']
            if p['dst'] is None:
                outputs[name] = outputs.get(name, []) + [(self.id, p)]

        return (inputs, outputs)


    def show(self, buf=sys.stdout, offset=0):
        lead = ' ' * offset
        buf.write(lead + str(self.id) + '. ' + self.__class__.__name__+ ' <' + self.name + "> ")
        buf.write('(' + ', '.join(p['name'] + (str(p['src']) if p['src'] else '') for p in self.inputs) + ' | ')
        buf.write(', '.join(p['name'] + (str(p['dst']) if p['dst'] else '') for p in self.outputs) + ')')
        buf.write('\n')

        if getattr(self, 'nodes', None):
            for id, node in self.nodes.items():
                node.show(buf, offset=offset+2)

    def add_wire_name(self, src_port_name, dst_vertex, dst_port_name):

        src_port = next(i for i, p in enumerate(self.outputs)
                        if p['name'] == src_port_name)
        dst_port = next(i for i, p in enumerate(dst_vertex.inputs)
                        if p['name'] == dst_port_name)

        self.add_wire(src_port, dst_vertex, dst_port)

    def add_wire(self, src_port, dst_vertex, dst_port):

        # Set port connection.
        self.outputs[src_port]['to'] = dst_vertex.inputs[dst_port]['queue']

        dst_vid = dst_vertex.inputs[dst_port]['vid']
        dst_vid = dst_vid if dst_vid else dst_vertex.id

        # Set source and destination ids.
        self.outputs[src_port]['dst'] = (dst_vid, dst_port)
        dst_vertex.inputs[dst_port]['src'] = (self.id, src_port)


class Net(Node):

    def __init__(self, name, inputs, outputs, nodes):
        super(Net, self).__init__(name, inputs, outputs)

        self.nodes = {n.id: n for n in nodes}


class Vertex(Node):

    def __init__(self, name, inputs, outputs):
        super(Vertex, self).__init__(name, inputs, outputs)

        # Initialize input queues.
        for p in self.inputs:
            p['queue'] = comm.Channel()

        # Flag indicating that the box is processing another message.
        self.busy = False

        self.departures = []

    #--------------------------------------------------------------------------

    def is_ready(self):

        '''
        Check if the condition on channels are sufficient for the vertex to
        start.

        NOTE: The very implementation applies for common types of vertices that
        need (1) at least one message on one of the inputs (2) all outputs to
        be available.
        '''
        # Test if there's an input message.
        input_ready = self.input_ready()

        # Test availability of outputs.
        output_ready = self.output_ready()

        return (input_ready, output_ready)

    # TODO: the method is run on the assumption that is_ready() returned True,
    # this creates undesirable logical dependence between these methods.
    def fetch(self):
        '''
        Fetch required number of message(s) from input queue(s) and return the
        data in the form suitable for processing pool.
        '''
        raise NotImplemented('The fetch method is not defined for the '
                             'abstract vertex.')

    def commit(self, response):
        '''
        Handle the result received from processing pool. Return the number of
        output messages sent.
        '''
        raise NotImplemented('The commit method is not defined for the '
                             'abstract vertex.')

    #--------------------------------------------------------------------------

    def input_ready(self, rng=None, any_channel=True, nmsg=1):
        '''
        Returns True if there's a msg in at least one channel from the range.
        '''
        if rng is None:
            rng = range(self.n_inputs)

        input_ready = True

        for port_id in rng:
            queue = self.inputs[port_id]['queue']

            ready = queue.size() >= nmsg

            if ready and any_channel:
                return True
            else:
                input_ready &= ready

        return input_ready

    def inputs_available(self):
        port_list = []

        for i, p in enumerate(self.inputs):
            if not p['queue'].is_empty():
                port_list.append(i)

        return port_list

    def output_ready(self, rng=None, space_needed=1):
        if rng is None:
            rng = range(self.n_outputs)

        for port_id in rng:
            to_queue = self.outputs[port_id]['to']

            if to_queue is None or not to_queue.is_space_for(space_needed):
                return False

        return True

    #--------------------------------------------------------------------------

    def send_dispatch(self, dispatch):

        for port_id, msgs in dispatch.items():
            port = self.outputs[port_id]

            for m in msgs:
                port['to'].put(m)

            self.departures.append(port['dst'])

    def send_out(self, mapping):

        for port_id, msg in mapping.items():
            port = self.outputs[port_id]

            port['to'].put(msg)
            self.departures.append(port['dst'])

    def send_to_range(self, msg, rng):
        mapping = {i: msg for i in rng}
        self.send_out(mapping)

    def send_to_all(self, msg):
        rng = range(self.n_outputs)
        self.send_to_range(msg, rng)

    def put_back(self, port_id, msg):
        self.inputs[port_id]['queue'].put_back(msg)

    #--------------------------------------------------------------------------

    def get(self, port_id):
        if port_id < 0 or port_id >= self.n_inputs:
            raise IndexError('Wrong number of input port.')

        port = self.inputs[port_id]

        m = port['queue'].get()

        return m

    def put(self, port_id, msg):
        self.inputs[port_id]['queue'].put(msg)

    #--------------------------------------------------------------------------


class StarNet(Vertex):

    def __init__(self, name, inputs, outputs, nodes):

        inputs += ['__result__', '__output__']
        super(StarNet, self).__init__(name, inputs, outputs)

        self.nodes = {n.id: n for n in nodes}

        self.stages = []
        self.stage_port = None
        self.merger = None

        for p in self.inputs[-2:]:
            p['queue'] = comm.Channel()

    def current_stage(self):
        if not self.stages:
            return None
        else:
            return self.stages[-1]


    def is_ready(self):
        if self.input_ready((1,2)):
            return (True, True)
        else:
            return (False, False)

    def fetch(self):

        import compiler.net.backend as compiler

        ready = self.inputs_available()

        result = {}

        for p in ready:

            msgs = []

            while self.input_ready(rng=(p,)):
                msgs.append(self.get(p))

            result[p] = msgs

        return result

    def wire_stages(self):
        stage = self.current_stage()

        if len(self.stages) == 1:

            # Mount main StarNet ports to the first stage (input) and to the
            # merger (output)
            self.inputs[0] = stage.inputs[0]
            self.outputs[0] = self.merger.outputs[0]

        # Mount result and output ports of the stage back to the StarNet
        stage.add_wire_name(self.stage_port, self, '__result__')
        stage.add_wire_name('__output__', self, '__output__')

        if len(self.stages) > 1:
            previous_stage = self.stages[-2]
            previous_stage.add_wire_name(self.stage_port, stage, self.stage_port)



class Box(Vertex):
    core = None
    pass


#------------------------------------------------------------------------------


class Transductor(Box):

    def __init__(self, name, inputs, outputs, core):
        super(Transductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):

        m = self.get(0)

        if m.is_segmark():
            # Special behaviour: sengmentation marks are sent through.
            self.send_to_all(m)
            return None

        else:
            return [m.content]

    def commit(self, response):

        if response.action == 'send':
            # Send output messages.
            self.send_out(response.out_mapping)
        else:
            print(response.action, 'is not implemented.')


class Printer(Transductor):
    '''
    Temporary class of vertex, just for debugging
    '''

    def fetch(self):
        m = self.get(0)
        return [m.content]

    def is_ready(self):

        # Check if there's an input message.
        input_ready = self.input_ready()
        return (input_ready, True)


class Executor(Box):
    '''
    Temporary class of vertex, just for debugging
    '''

    def __init__(self, name, inputs, outputs, core):
        super(Executor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):
        inputs = self.inputs_available()
        m = [(pid, self.inputs[pid]['name'], self.get(pid)) for pid in inputs]
        return [m]

    def is_ready(self):

        # Check if there's an input message.
        input_ready = self.input_ready()
        return (input_ready, True)

    def commit(self, response):
        pass


class Inductor(Box):

    def __init__(self, name, inputs, outputs, core):
        super(Inductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):
        m = self.get(0)

        if m.is_segmark():
            # Special behaviour for segmentation marks.
            m.plus()
            self.send_to_all(m)
            return None

        else:
            return [m.content]

    def commit(self, response):

        if response.action == 'continue':

            cont = response.aux_data

            # Put the continuation back to the input queue
            self.put_back(0, cont)

            self.send_out(response.out_mapping)

        elif response.action == 'terminate':
            self.send_out(response.out_mapping)

        else:
            print(response.action, 'is not implemented.')


class DyadicReductor(Box):

    def __init__(self, name, inputs, outputs, core, ordered, segmented):
        super(DyadicReductor, self).__init__(name, inputs, outputs)
        self.core = core

        self.ordered = ordered
        self.segmented = segmented

    def is_ready(self):

        ## Test input availability.
        #

        # Reduction start: 2 messages from both channel are needed.
        input_ready = self.input_ready(any_channel=False)

        ## Test output availability.
        #

        output_ready = self.output_ready(range(1, self.n_outputs))
        # Test the 1st output separately since it must have enough space
        # for segmentation mark.
        output_ready &= self.output_ready((0,), space_needed=2)

        return (input_ready, output_ready)

    def fetch(self):

        # First reduction operand:
        term_a = self.get(0)

        if term_a.is_segmark():
            # Special behaviour for segmentation marks.
            term_a.plus()
            self.send_to_range(term_a, range(1, self.n_outputs))
            return None

        # Second reduction operand
        term_b = self.get(1)

        if term_b.is_segmark():
            # Special behaviour for segmentation marks.
            self.send_out({0: term_a})

            if term_b.n != 1:
                if term_b.n > 1:
                    term_b.minus()
                self.send_out({0: term_b})

            return None

        # Input messages are not segmarks: pass them to coordinator.
        return [term_a.content, term_b.content]

    def commit(self, response):

        if response.action == 'partial':
            # First output channel cannot be the destination of partial result.
            assert(0 not in response.out_mapping)
            self.send_out(response.out_mapping)

            # Put partial reduction result to the first input channel for
            # further reduction.
            self.put_back(0, response.aux_data)

        else:
            print(response.action, 'is not implemented.')


class MonadicReductor(Box):

    def __init__(self, name, inputs, outputs, core, ordered, segmented):
        super(MonadicReductor, self).__init__(name, inputs, outputs)
        self.core = core

        self.ordered = ordered
        self.segmented = segmented

    def is_ready(self):

        ## Test input availability.
        #

        # Reduction start: 2 messages from the input channel are needed.
        input_ready = self.input_ready(nmsg=2)

        ## Test output availability.
        #

        output_ready = self.output_ready(range(1, self.n_outputs))
        # Test the 1st output separately since it must have enough space
        # for segmentation mark.
        output_ready &= self.output_ready((0,), space_needed=2)

        return (input_ready, output_ready)

    def fetch(self):

        # First reduction operand:
        term_a = self.get(0)

        if term_a.is_segmark():
            # Special behaviour for segmentation marks.

            sm_b = comm.SegmentationMark(term_a.n)
            sm_b.plus()
            self.send_to_range(sm_b, range(1, self.n_outputs))

            if term_a.n != 1:
                sm_a = comm.SegmentationMark(term_a.n)
                if term_a.n > 1:
                    sm_a.minus()
                self.send_to_range(sm_a, (0,))

            return None

        # Second reduction operand
        term_b = self.get(0)

        if term_b.is_segmark():
            # Special behaviour for segmentation marks.

            # Partial result becomes final.
            self.send_out({0: term_a})

            sm_b = comm.SegmentationMark(term_b.n)
            sm_b.plus()
            self.send_to_range(sm_b, range(1, self.n_outputs))

            if term_b.n != 1:
                sm_a = comm.SegmentationMark(term_b.n)
                if term_b.n > 1:
                    sm_a.minus()
                self.send_to_range(sm_a, (0,))

            return None

        # Input messages are not segmarks: pass them to coordinator.
        return [term_a.content, term_b.content]

    def commit(self, response):

        if response.action == 'partial':
            # First output channel cannot be the destination of partial result.
            assert(0 not in response.out_mapping)
            self.send_out(response.out_mapping)

            # Put partial reduction result to the first input channel for
            # further reduction.
            self.put_back(0, response.aux_data)

        else:
            print(response.action, 'is not implemented.')


class Merger(Box):

    def __init__(self, name, inputs, outputs, core=None):
        super(Merger, self).__init__(name, inputs, outputs)

    def fetch(self):
        for i in range(self.n_inputs):
            try:
                m = self.get(i)
                self.send_to_all(m)

            except comm.Empty:
                continue
        return None


#------------------------------------------------------------------------------


class Sync(Vertex):

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

        old_st = self.state.name

        self.run()

        print(self.id, old_st, '->', self.state.name)

        return None

    def run(self):

        transition = self.port_handler.choose_transition()

        if transition is None:
            return

        transition.hit()

        # 1. Assign
        transition.assign()

        # 2. Send
        dispatch = transition.send()
        #print('D', self.id, dispatch)
        self.send_dispatch(dispatch)

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
            self.local_aliases[depth] = msg.n
            self.scope.add_from(self.local_aliases)

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

            dispatch[port] = dispatch.get(port, []) + [outcome]

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
        raise NotImplemented('Set method not implemented for generic type.')


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
        if True: # value >= (- 2 ** (self.width - 1)) and value <= (2 ** (self.width - 1) - 1):
            self.value = value
        else:
            raise RuntimeError('Value %d is out of range for int width %d.'
                               % (value, self.width))

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

