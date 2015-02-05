#!/usr/bin/env python3

import sys
import communication as comm
from collections import Sequence


class Port:
    def __init__(self, name, id, sid=None):
        self.name = name
        self.id = id
        self.sid = sid

        self.channel = None


class Stream:
    def __init__(self, src=None, dst=None, channel=None):
        self.src = src
        self.dst = dst
        self.channel = channel
        self.taken = False


class Node:
    '''
    Superclass of runtime components. Defines abstract execution interface and
    communication facilities.

    Attributes:
        id (int): identifier of the node within the enclosed ``Net``. Equals
            0 if the node is the root of the network, greater than 0 otherwise.
        name (str): node name from the network description.
        path (tuple of int): sequence of identifiers leading from the root of
            the network to the node.
        ast (compiler.net.ast.Node): abstract syntax tree of the node assigned
            for possible usage at runtime.
        executable (bool): indicates whether the node can accept and proccess
            messages by its own.
        busy (bool): indicates that the node is processing message(s) and
            cannot read any more ones.
        departures (set of int): identifiers of output ports to which messages
            have been sent by the node.
        inputs (dict of int:Port pairs): input ports of the node.
        outputs (dict of int:Port pairs): output ports of the node.
    '''

    def __init__(self, name, inputs, outputs):

        self.id = None

        self.name = name

        self.path = None
        self.ast = None

        self.executable = False
        self.busy = False

        self.departures = set()

        # Initialise ports
        self.inputs = {port_id: Port(name, port_id)
                       for port_id, name in enumerate(inputs)}
        self.outputs = {port_id: Port(name, port_id)
                        for port_id, name in enumerate(outputs)}

    #--------------------------------------------------------------------------

    @property
    # TODO: remove
    def n_inputs(self):
        return len(self.inputs)

    @property
    # TODO: remove
    def n_outputs(self):
        return len(self.outputs)


    def free_ports(self):
        '''
        Get identifiers of input and outputs ports that are not connected to
        any stream.

        Returns:
            tuple of the following structure::
                (# Input ports:
                    {
                        <port-name>: [(<node-id>, <port-id>), ...)],
                        ...
                    },
                 # Output ports:
                    {
                        # Likewise
                        ...
                    }
                )
        '''

        inputs = {}
        outputs = {}

        def get_free_ports(ports):
            acc = {}
            for i, p in ports.items():
                name = p.name
                if p.sid is None:
                    acc[name] = acc.get(name, []) + [(self.id, p.id)]
            return acc

        inputs = get_free_ports(self.inputs)
        outputs = get_free_ports(self.outputs)

        return (inputs, outputs)

    def _get_input_channel(self, port_id):
        return self.inputs[port_id].channel

    def _get_output_channel(self, port_id):
        return self.outputs[port_id].channel

    #--------------------------------------------------------------------------

    def is_input_ready(self, rng=None, any_port=True, nmsg=1):
        '''
        Returns True if there's a msg in at least one channel from the range.
        '''
        if rng is None:
            rng = self.inputs.keys()

        input_ready = True

        for port_id in rng:
            channel = self._get_input_channel(port_id)

            ready = channel.size() >= nmsg

            if ready and any_port:
                return True
            else:
                input_ready &= ready

        return input_ready

    def get_ready_inputs(self, rng=None):

        port_list = []

        if rng is None:
            rng = self.inputs.keys()

        for port_id in rng:
            channel = self._get_input_channel(port_id)
            if not channel.is_empty():
                port_list.append(port_id)

        return port_list

    def is_output_unblocked(self, rng=None, space_needed=1):

        if rng is None:
            rng = self.outputs.keys()

        for port_id in rng:
            channel = self._get_output_channel(port_id)

            if not channel.is_space_for(space_needed):
                return False

        return True

    #--------------------------------------------------------------------------

    def send_dispatch(self, dispatch):

        for port_id, msgs in dispatch.items():
            channel = self._get_output_channel(port_id)

            for m in msgs:
                channel.put(m)

            self.departures.add(port_id)

    def send_to_range(self, msg, rng):
        dispatch = {i: [msg] for i in rng}
        self.send_dispatch(dispatch)

    def send_to_all(self, msg):
        self.send_to_range(msg, self.outputs.keys())

    def put_back(self, port_id, msg):
        channel = self._get_input_channel(port_id)
        channel.put_back(msg)

    #--------------------------------------------------------------------------

    def get(self, port_id):
        channel = self._get_input_channel(port_id)
        return channel.get()

    def put(self, port_id, msg):
        channel = self._get_input_channel(port_id)
        channel.put(msg)

    #--------------------------------------------------------------------------

    def show(self, buf=sys.stdout, offset=0):
        lead = ' ' * offset
        buf.write(lead + str(self.id)
                  + '. ' + self.__class__.__name__+ ' <' + self.name + "> ")

        ports = lambda ports:\
            ', '.join('%s%s' % (p.name, ('[%s]' % p.sid if p.sid else ''))
                      for i, p in ports.items())

        buf.write("(%s | %s)\n" % (ports(self.inputs), ports(self.outputs)))

        if getattr(self, 'nodes', None):
            for id, node in self.nodes.items():
                node.show(buf, offset=offset+2)

    #--------------------------------------------------------------------------

    #--------------------------------------------------------------------------

    def is_ready(self):
        '''
        Test if the vertex if ready to execute.

        Returns:
            (tuple of bool): two Boolean values indicating readines of the
                vertex respectively for input and output channels.
        '''
        raise NotImplementedError('The is_ready method is not defined for the '
                                  'abstract vertex.')

    def fetch(self):
        '''
        Fetch required number of message(s) from input channel(s) and return
        their contents.

        Returns:
            (list): contents of the fetched messages.
        '''
        raise NotImplementedError('The fetch method is not defined for the '
                                  'abstract vertex.')

    def run(self, msgs):
        raise NotImplementedError('The run method is not defined for the '
                                  'abstract vertex.')

    def commit(self, response):
        '''
        Handle the result received from processing pool. Return the number of
        output messages sent.

        Args:
            response (tuple): the computation result received from the pool.
        '''
        raise NotImplementedError('The commit method is not defined for the '
                                  'abstract vertex.')


class Net(Node):
    '''
    Node representing a subnetwork which can consist of both vertices and other
    nets. By default the net is not executable.

    Attributes:
        nodes (dict of Node): internal nodes of the net indexed by identifiers.
    '''


    def __init__(self, name, inputs, outputs):
        super(Net, self).__init__(name, inputs, outputs)

        self._node_id = 1
        self.nodes = {}

        self.streams = {}

        # Initialise external virtual streams.
        for i in range(self.n_inputs):
            sid = self._get_ext_stream_input(i)
            self.streams[sid] = Stream(src=(-1, i))
        for i in range(self.n_outputs):
            sid = self._get_ext_stream_output(i)
            self.streams[sid] = Stream(dst=(-1, i))

        self._sid = 1

    #--------------------------------------------------------------------------

    def get_node_by_path(self, path):
        '''
        Accepts path of a node in the network, select the next ``Net`` and
        call the method recursively for the subsequent relative path. The empty
        path means refers to the ``self`` object.

        Returns:
            Node: the requested node once the only identifier left in the path,
                or ``self`` object if the path is empty.

        Raises:
            ValueError: the path is malformed.
            IndexError: the subsequent node is not in the net or its type
                other than ``Net``.
        '''

        if not isinstance(path, Sequence):
            raise ValueError('The path must be an ordered sequence.')

        if not path:
            return self

        node_id, further_path = path

        if node_id not in self.nodes:
            raise IndexError('The requested node with id=%d not found in the'
                             'net ``%s\'\'' % (node_id, self.name))

        node = self.nodes[node_id]

        if further_path:
            # The selected node is not final

            if not hasattr(node, 'nodes'):
                raise IndexError('A vertex occured in the middle of the path.')

            node.get_node_by_path(further_path)

        else:
            # Final node
            return node

    #--------------------------------------------------------------------------

    def _get_ext_stream_input(self, port_id):
        '''
        Calculate external stream identifier for a given input port. By
        convention, the identifiers are less than zero and cannot coincide with
        the ones for outputs.

        Args:
            port_id (int): identifier of the input port.

        Returns:
            int: stream identifier less than zero.

        Raises:
            ValueError: the resulting ID greater of equals zero.
        '''
        stream_id = - (port_id + 1)

        if stream_id > 0:
            raise ValueError('The port identifier (%d) is malformed since it '
                             'causes a negative stream ID: %d.'
                             % (port_id, stream_id))
        return stream_id

    def _get_ext_stream_output(self, port_id):
        '''
        See `_get_ext_stream_input`_.
        '''
        stream_id = - (10000 + port_id)

        if stream_id > 0:
            raise ValueError('The port identifier (%d) is malformed since it '
                             'causes a negative stream ID: %d.'
                             % (i, stream_id))
        return stream_id

    def _alloc_new_node_id(self):
        '''
        Allocate new identifier for an internal node.

        Returns:
            int: new node identifier.
        '''
        t = self._node_id
        self._node_id += 1
        return t

    def add_node(self, obj):
        nid = self._alloc_new_node_id()
        obj.id = nid
        self.nodes[nid] = obj
        return nid

    def get_node(self, node_id):
        '''
        Get node object by its identifier within the net. Returns ``self``
        object if the ID is zero.

        Args:
            node_id (int): node identifier within the net, or zero.

        Returns:
            A node with the given ID or ``self`` object if the ID is zero.

        Raises:
            IndexError: the ID not found in the new.
        '''

        if node_id == 0:
            return self

        if node_id not in self.nodes:
            raise IndexError('The node identifier (%d) not found in the net '
                             '``%s\'\'' % (node_id, self.name))

        return self.nodes[node_id]

    def _alloc_new_stream(self):
        '''
        Allocate new stream in the net.

        Returns:
            int: identifier of the new stream.
        '''

        free_streams = [i for i, stream in self.streams.items()
                        if stream.taken is False and i > 0]

        if not free_streams:
            # All streams are taken - create a new one.
            s = self._sid
            self._sid += 1
            self.streams[s] = Stream(channel=comm.Channel())
        else:
            # Choose any free stream.
            s = free_streams.pop()

        self.streams[s].taken = True
        return s

    def init_ext_streams(self):
        '''
        Append virtual streams to ports of the net.
        '''
        for i, stream in self.streams.items():
            if i < 0:
                stream.channel = comm.Channel()

        for i, port in self.inputs.items():
            port.sid = self._get_ext_stream_input(i)

        for i, port in self.outputs.items():
            port.sid = self._get_ext_stream_output(i)


    # TODO: recursive version.
    def update_channels(self, node_id):
        '''
        Insert stream channels to ports of the given node within the net.

        Args:
            node_id (int): node ID within the net.
        '''
        node = self.get_node(node_id)

        for i, port in node.inputs.items():
            if port.sid:
                # TODO: make a stub for disconnected ports.
                port.channel = self.streams[port.sid].channel

        for i, port in node.outputs.items():
            if port.sid:
                port.channel = self.streams[port.sid].channel

    #--------------------------------------------------------------------------

    def add_wire(self, src, dst):
        '''
        Establish a connection between an output and input endpoints within the
        net.

        Args:
            src (tuple of int): source endpoind of the form (<node-id>, <port-id>).
            dst (tuple of int): destination endpoind, likewise.

        Raises:
            IndexError: a port identifier not found in the given node.
        '''

        sid = self._alloc_new_stream()
        stream = self.streams[sid]
        stream.taken = True

        stream.src = src
        stream.dst = dst

        # Source endpoint.
        src_node = self.get_node(src[0])

        if src[1] not in src_node.outputs:
            raise IndexError('Output port id=`%d\' not found in the node `%s\''
                             % (src[1], src_node.name))

        src_node.outputs[src[1]].sid = sid

        # Destination endpoint.
        dst_node = self.get_node(dst[0])

        if dst[1] not in dst_node.inputs:
            raise IndexError('Input port id=`%d\' not found in the node `%s\''
                             % (dst[1], dst_node.name))

        dst_node.inputs[dst[1]].sid = sid

    def mount_input_port(self, ext_port_id, endpoint):
        sid = self._get_ext_stream_input(ext_port_id)
        stream = self.streams[sid]
        stream.taken = True

        stream.src = (-1, ext_port_id)
        stream.dst = endpoint

        dst_node = self.nodes[endpoint[0]]
        dst_node.inputs[endpoint[1]].sid = sid


    def mount_output_port(self, ext_port_id, endpoint):
        sid = self._get_ext_stream_output(ext_port_id)
        stream = self.streams[sid]
        stream.taken = True

        stream.dst = (-1, ext_port_id)
        stream.src = endpoint

        src_node = self.nodes[endpoint[0]]
        src_node.outputs[endpoint[1]].sid = sid


class Vertex(Node):

    def __init__(self, name, inputs, outputs):
        super(Vertex, self).__init__(name, inputs, outputs)

        self.executable = True


class Box(Vertex):

    def __init__(self, name, inputs, outputs, core):
        super(Box, self).__init__(name, inputs, outputs)

        self._core = None
        self.core = core

    @property
    def core(self):
        if not self._core:
            raise ValueError('Function of the box `%s\' is not set.'
                             % self.name)
        return self._core

    @core.setter
    def core(self, func):
        if not callable(func):
            raise ValueError('Box function must by a callable object.')
        self._core = func

    #--------------------------------------------------------------------------

    def _make_task(self, *args):
        return (self.core, {'vertex_id': self.path, 'args': args})


class Transductor(Box):

    def __init__(self, name, inputs, outputs, core):
        super(Transductor, self).__init__(name, inputs, outputs, core)

    def is_ready(self):
        # Test if there's an input message.
        is_input_msg = self.is_input_ready()

        # Test availability of outputs.
        output_ready = self.is_output_unblocked()

        return (is_input_msg, output_ready)

    def fetch(self):
        m = self.get(0)
        return [m]

    def run(self, msgs):
        assert(len(msgs) == 1)
        m = msgs[0]

        if m.is_segmark():
            # Special behaviour: segmentation marks are sent through.
            self.send_to_all(m)
            return None

        return self._make_task(m.content)

    def commit(self, response):

        if response.action == 'send':
            # Send output messages.
            self.send_dispatch(response.dispatch)
        else:
            print(response.action, 'is not implemented.')


class Executor(Box):

    def __init__(self, name, inputs, outputs, core):
        super(Executor, self).__init__(name, inputs, outputs, core)

    def is_ready(self):
        # Check if there's an input message.
        is_input_msg = self.is_input_ready()
        return (is_input_msg, True)

    def fetch(self):
        ready_inputs = self.get_ready_inputs()
        m = [(pid, self.inputs[pid].name, self.get(pid)) for pid in ready_inputs]
        return m

    def run(self, msgs):
        return self._make_task(msgs)

    def commit(self, response):
        pass


class Inductor(Box):

    def __init__(self, name, inputs, outputs, core):
        super(Inductor, self).__init__(name, inputs, outputs, core)

        self.segflag = False

    def is_ready(self):
        # Test if there's an input message.
        is_input_msg = self.is_input_ready()

        # Test availability of outputs.
        output_ready = self.is_output_unblocked()

        return (is_input_msg, output_ready)

    def fetch(self):
        m = self.get(0)
        return [m]

    def run(self, msgs):
        assert(len(msgs) == 1)
        m = msgs[0]

        if m.is_segmark():
            # Special behaviour for segmentation marks.
            m.plus()
            self.send_to_all(m)
            self.segflag = False
            return None

        else:
            if self.segflag:
                self.send_to_all(comm.SegmentationMark(1))
                self.segflag = False

            return self._make_task(m.content)

    def commit(self, response):

        if response.action == 'continue':

            cont = response.aux_data

            # Put the continuation back to the input queue
            self.put_back(0, cont)

            self.send_dispatch(response.dispatch)

        elif response.action == 'terminate':
            self.send_dispatch(response.dispatch)
            self.segflag = True

        else:
            print(response.action, 'is not implemented.')


class DyadicReductor(Box):

    def __init__(self, name, inputs, outputs, core, ordered, segmented):
        super(DyadicReductor, self).__init__(name, inputs, outputs, core)

        self.ordered = ordered
        self.segmented = segmented

        self._main_output = 0
        self._aux_outputs = [port_id for port_id in self.outputs
                             if port_id != self._main_output]

    def is_ready(self):

        ## Test input availability.
        # Reduction start: 2 messages from both channel are needed.
        is_input_msg = self.is_input_ready(any_port=False)

        ## Test output availability.
        output_ready = self.is_output_unblocked(self._aux_outputs)

        # Test the 1st output separately since it must have enough space
        # for segmentation mark.
        output_ready &= self.is_output_unblocked((self._main_output,),
                                                 space_needed=2)
        return (is_input_msg, output_ready)

    def fetch(self):
        return [self.get(i) for i in (0, 1)]

    def run(self, msgs):
        assert(len(msgs) == 2)
        term_a, term_b = msgs

        if term_a.is_segmark():
            # Special behaviour for segmentation marks.
            term_a.plus()
            self.send_to_range(term_a, self._aux_outputs)
            self.put_back(1, term_b)
            return None

        if term_b.is_segmark():
            # Special behaviour for segmentation marks.
            self.send_dispatch({self._main_output: [term_a]})

            if term_b.n != 1:
                if term_b.n > 1:
                    term_b.minus()
                self.send_dispatch({self._main_output: [term_b]})
            return None

        return self._make_task(term_a.content, term_b.content)

    def commit(self, response):

        if response.action == 'partial':
            # First output channel cannot be the destination of partial result.
            assert(0 not in response.dispatch)
            self.send_dispatch(response.dispatch)

            # Put partial reduction result to the first input channel for
            # further reduction.
            self.put_back(0, response.aux_data)

        else:
            print(response.action, 'is not implemented.')


class MonadicReductor(Box):

    def __init__(self, name, inputs, outputs, core, ordered, segmented):
        super(MonadicReductor, self).__init__(name, inputs, outputs, core)

        self.ordered = ordered
        self.segmented = segmented

        self._main_output = 0
        self._aux_outputs = [port_id for port_id in self.outputs
                             if port_id != self._main_output]

    def is_ready(self):
        ## Test input availability.
        # Reduction start: 2 messages from the input channel are needed.
        is_input_msg = self.is_input_ready(nmsg=2)

        ## Test output availability.
        output_ready = self.is_output_unblocked(self._aux_outputs)

        # Test the 1st output separately since it must have enough space
        # for segmentation mark.
        output_ready &= self.is_output_unblocked((self._main_output,),
                                                 space_needed=2)
        return (is_input_msg, output_ready)

    def fetch(self):
        return [self.get(0) for i in range(2)]

    def run(self, msgs):
        assert(len(msgs) == 2)
        term_a, term_b = msgs

        if term_a.is_segmark():
            # Special behaviour for segmentation marks.
            sm_b = comm.SegmentationMark(term_a.n)
            sm_b.plus()
            self.send_to_range(sm_b, self._aux_outputs)

            if term_a.n != 1:
                sm_a = comm.SegmentationMark(term_a.n)
                if term_a.n > 1:
                    sm_a.minus()
                self.send_to_range(sm_a, (self._main_output,))

            self.put_back(0, term_b)
            return None

        if term_b.is_segmark():
            # Special behaviour for segmentation marks.

            # Partial result becomes final.
            self.send_dispatch({0: [term_a]})

            sm_b = comm.SegmentationMark(term_b.n)
            sm_b.plus()
            self.send_to_range(sm_b, self._aux_outputs)

            if term_b.n != 1:
                sm_a = comm.SegmentationMark(term_b.n)
                if term_b.n > 1:
                    sm_a.minus()
                self.send_to_range(sm_a, (self._main_output,))
            return None

        # Input messages are not segmarks: pass them to coordinator.
        return self._make_task(term_a.content, term_b.content)

    def commit(self, response):

        if response.action == 'partial':
            # First output channel cannot be the destination of partial result.
            assert(0 not in response.dispatch)
            self.send_dispatch(response.dispatch)

            # Put partial reduction result to the first input channel for
            # further reduction.
            self.put_back(0, response.aux_data)

        else:
            print(response.action, 'is not implemented.')


class Merger(Vertex):

    def __init__(self, name, inputs, outputs):
        super(Merger, self).__init__(name, inputs, outputs)

        self.nterm = 0

    def is_ready(self):
        # Test if there's an input message.
        is_input_msg = self.is_input_ready()

        # Test availability of outputs.
        output_ready = self.is_output_unblocked()

        return (is_input_msg, output_ready)

    def fetch(self):
        msgs = []
        for i in self.inputs:
            try:
                m = self.get(i)
                msgs.append(m)
            except comm.Empty:
                continue
        return msgs

    def run(self, msgs):
        for m in msgs:
            if m.is_segmark() and m.n == 0:
                self.nterm += 1
                if self.nterm == self.n_inputs:
                    self.send_to_all(m)
            else:
                self.send_to_all(m)
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

        for i, port in self.outputs.items():
            if not port.channel.is_space_for(1):
                blocked.add(i)

        return blocked

    #---------------------------------------------------

    def is_ready(self):

        # Inputs with messages available
        get_ready_inputs = self.get_ready_inputs()

        # Inputs that can cause transitions from the current state
        inputs_feasible = set(get_ready_inputs) & set(self.state.inputs())

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

        return (self.this['msg'],)

    def run(self, msgs):

        transition = self.port_handler.choose_transition()

        if transition is None:
            return

        transition.hit()

        # 1. Assign
        transition.assign()

        # 2. Send
        dispatch = transition.send()
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

        return None

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

                result = self._compute_dataexp(dataexp[1])
                if type(result) is int:
                    outcome = comm.SegmentationMark(result)
                elif type(result) is dict:
                    outcome = comm.Record(result)
                else:
                    raise AssertionError('Wrong dataexp.')

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

        if len(items) == 1 and items[0][0] == 'ItemThis':
            if self.this['msg'].is_segmark():
                return self.this['msg'].n
            else:
                return self.this['msg'].content

        for item in items:

            if item[0] == 'ItemThis':
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

