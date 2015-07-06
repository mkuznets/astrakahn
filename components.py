#!/usr/bin/env python3

import sys
import communication as comm
from collections import Sequence, deque, namedtuple


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
        _busy (bool): indicates that the node is processing message(s) and
            cannot read any more ones.
        departures (set of int): identifiers of output ports to which messages
            have been sent by the node.
        inputs (dict of int:<list of port pairs>): input ports of the node.
        outputs (dict of int:<list of port pairs>): output ports of the node.
    '''

    def __init__(self, name, inputs, outputs):

        self.id = None

        self.name = name

        self.path = None
        self.ast = None

        self.executable = False
        self._busy = False

        self.departures = set()

        # Initialise ports
        self.inputs = {port_id: Port(name, port_id)
                       for port_id, name in enumerate(inputs)}
        self.masked_inputs = {}

        self.outputs = {port_id: Port(name, port_id)
                        for port_id, name in enumerate(outputs)}
        self.masked_outputs = {}

    #--------------------------------------------------------------------------

    @property
    def busy(self):
        return self._busy

    @busy.setter
    def busy(self, value):
        self._busy = bool(value)

    #--------------------------------------------------------------------------

    @property
    def n_inputs(self):
        return len(self.inputs)

    @property
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

        # In some cases (e.g. for Mergers) the vertex may not have any input
        # ports. Apparently, such vertices cannot be `ready'.
        if not self.inputs:
            return False

        if rng is None:
            rng = self.inputs.keys()

        input_ready = True

        channels = list(filter(None, [self._get_input_channel(i) for i in rng]))

        if not channels:
            return False

        for channel in channels:

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
            if channel and not channel.is_empty():
                port_list.append(port_id)

        return port_list

    def is_output_unblocked(self, rng=None, space_needed=1):

        if rng is None:
            rng = self.outputs.keys()

        for port_id in rng:
            channel = self._get_output_channel(port_id)

            if channel and not channel.is_space_for(space_needed):
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
            ', '.join('%s%s%s' % (p.name, ('[%s]' % p.sid if p.sid else ''),
                                   '[*]' if p.channel else '[]')
                      for i, p in ports.items())

        buf.write("(%s | %s)\n" % (ports(self.inputs), ports(self.outputs)))

        if getattr(self, 'nodes', None):
            for id, node in self.nodes.items():
                node.show(buf, offset=offset+2)

    #--------------------------------------------------------------------------

    def _add_ports(self, n_ports, ports):
        port_id = (max(ports) + 1) if ports else 0
        port_names = {i: '_%s' % i for i in range(port_id, port_id+n_ports)}

        for port_id, name in port_names.items():
            ports[port_id] = Port(name, port_id)

        return tuple(port_names)

    def add_input_ports(self, n_ports):
        return self._add_ports(n_ports, self.inputs)

    def add_output_ports(self, n_ports):
        return self._add_ports(n_ports, self.outputs)

    def _mask_ports(self, n, ports, masked):
        if len(ports) - n >= 1:
            masked.update(dict(ports.popitem() for i in range(n)))

    def mask_input_ports(self, n):
        return self._mask_ports(n, self.inputs, self.masked_inputs)

    def mask_output_ports(self, n):
        return self._mask_ports(n, self.outputs, self.masked_outputs)

    def change_ports(self, n_in, n_out):
        def _change(n, ports, masked, add, mask):
            if n > 0:
                n_unmask = 0
                if masked:
                    n_unmask = min(len(masked), n)
                    ports.update(dict(masked.popitem() for i in range(n_unmask)))
                new_ports = add(n - n_unmask)
                return new_ports
            elif n < 0:
                mask(-n)

        new_inputs = _change(n_in, self.inputs, self.masked_inputs,
                             self.add_input_ports, self.mask_input_ports)

        new_outputs = _change(n_out, self.outputs, self.masked_outputs,
                              self.add_output_ports, self.mask_output_ports)

        return (new_inputs, new_outputs)

    #--------------------------------------------------------------------------

    def is_ready(self):
        '''
        Test if the vertex if ready to execute.

        Returns:
            (tuple of bool): two Boolean values indicating readines of the
                vertex respectively for input and output channels.
        '''
        raise NotImplementedError('The is_ready method is not defined for the '
                                  'abstract vertex: %s.' %
                                  self.__class__.__name__)

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
        self.fire_nodes = set()

    #--------------------------------------------------------------------------

    def get_parent_net(self, path):
        return self.get_node_by_path(path[:-1])

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

        node_id, *further_path = path

        if node_id not in self.nodes:
            raise IndexError('The requested node with id=%d not found in the '
                             'net ``%s\'\'' % (node_id, self.name))

        node = self.nodes[node_id]

        if further_path:
            # The selected node is not final

            if not hasattr(node, 'nodes'):
                raise IndexError('A vertex occured in the middle of the path.')

            return node.get_node_by_path(further_path)

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

        # Path of the net is now known during the initial construction (compile
        # time), but known in runtime.
        if self.path:
            obj.path = tuple(self.path + (nid,))

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


    def make_root(self):
        '''
        Append channels to the external streams. For a top level net it allows
        an outside coordinator to put and get messages directly from the net.
        '''
        for i, stream in self.streams.items():
            if i < 0:
                stream.channel = comm.Channel()

        for i, port in self.inputs.items():
            port.sid = self._get_ext_stream_input(i)

        for i, port in self.outputs.items():
            port.sid = self._get_ext_stream_output(i)

    # TODO: recursive version.
    def init_ext_streams(self, node_id):
        '''
        Args:
            node_id (int): node ID within the net.
        '''
        node = self.get_node(node_id)

        def init(node, ports, get_ext_f):
            for i, port in ports.items():
                if port.sid:
                    get_ext = getattr(node, get_ext_f)
                    ext_sid = get_ext(i)
                    node.streams[ext_sid].channel = self.streams[port.sid].channel

        init(node, node.inputs, '_get_ext_stream_input')
        init(node, node.outputs, '_get_ext_stream_output')

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


#--------------------------------------------------------------------------

class Morphism(Net):

    def __init__(self, name, inputs, outputs, inductor, transductor, reductor):
        assert(len(inputs) == 2)
        assert(len(outputs) >= 2)

        super(Morphism, self).__init__(name, inputs, outputs)

        # Add components to network.
        inductor_id = self.add_node(inductor)
        transductor_id = self.add_node(transductor)
        reductor_id = self.add_node(reductor)

        import libmorph as lib

        marker_id = self.add_node(lib.build_marker())
        router_id = self.add_node(lib.build_router(0))

        merger = Merger('MorphMerger', inputs, [outputs[0]])
        merger_id = self.add_node(merger)

        # Construct the network.
        self.mount_input_port(0, (marker_id, 0))
        self.mount_input_port(1, (merger_id, 1))

        self.add_wire((marker_id, 0), (merger_id, 0))
        self.add_wire((merger_id, 0), (transductor_id, 0))
        self.add_wire((transductor_id, 0), (router_id, 0))
        self.add_wire((router_id, 0), (reductor_id, 0))

        self.mount_output_port(0, (reductor_id, 0))
        self.mount_output_port(1, (router_id, 1))

        for port_id in range(1, len(transductor.outputs)):
            self.mount_output_port(port_id+1, (transductor_id, port_id))

#--------------------------------------------------------------------------

class SynchTable(Net):

    def __init__(self, name, inputs, outputs, sync_ast, labels):
        super(SynchTable, self).__init__(name, inputs, outputs)
        self.executable = True

        self.ready_port = None

        self.sync_ast = sync_ast
        self.labels = labels

        self.syncs = {}

        self.mergers = []

        for pid, port in self.outputs.items():
            mrg = Merger('m%d' % pid, [], [port.name])

            mrgid = self.add_node(mrg)
            self.mount_output_port(pid, (mrgid, 0))

            self.mergers.append(mrgid)

    def is_ready(self):

        input_ports = self.get_ready_inputs()

        for port_id in input_ports:
            ready = True

            for sync in self.syncs.values():
                channel = sync._get_input_channel(port_id)

                if not channel.is_space_for(1):
                    ready = False
                    break

            if ready:
                self.ready_port = port_id
                return (True, True)

        return (False, False)

    def fetch(self):
        m = self.get(self.ready_port)
        return [m]

    def run(self, msgs):
        msg = msgs[0]

        label_values = []

        if self.labels not in msg:
            raise RuntimeError('Label %s is not found in the message %s' %
                               (label, msg))

        st = tuple(msg[label] for label in self.labels)

        # Spawn new synchroniser if needed.
        if st not in self.syncs:
            from compiler.sync.backend import SyncBuilder

            # Set the configurations.
            for name, value in zip(self.labels, st):
                for c in self.sync_ast.configs[name]:
                    c.value = value

            sb = SyncBuilder()
            obj = sb.traverse(self.sync_ast)

            syncid = self.add_node(obj)

            # Associate sync's input ports with fictitious streams.
            for pid, port in obj.inputs.items():
                sid = self._alloc_new_stream()
                port.sid = sid

            # Connect sync's output ports to mergers.
            for i, mid in enumerate(self.mergers):
                # Add new ports to each Merger
                merger = self.get_node(mid)
                (port, *_), _ = merger.change_ports(1, 0)
                self.add_wire((syncid, i), (mid, port))

                self.syncs[st] = obj

                self.update_channels(mid)

            self.update_channels(syncid)

        self.show()

        # Route the message to corresponding sync.

        sync = self.syncs[st]
        self.fire_nodes.add(sync.path)
        sync.put(self.ready_port, msg)


#--------------------------------------------------------------------------

class Transductor(Box):

    def __init__(self, name, inputs, outputs, core):
        assert(len(inputs) == 1)
        super(Transductor, self).__init__(name, inputs, outputs, core)

        self.max_inst = 1
        self.n_inst = 0

        self.msgs_unord = deque()
        self.msgs_ord = {}
        self.top = 0

    #--------------------------------------------------------------------------

    @property
    def busy(self):
        return self.n_inst >= self.max_inst or self._busy

    @busy.setter
    def busy(self, value):
        pass

    #--------------------------------------------------------------------------

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

        if self.msgs_ord or self.msgs_unord:
            if self._release():
                self.put_back(0, m)
                return None

        if m.is_segmark():
            # Special behaviour: segmentation marks are sent through.
            if self.n_inst == 0:
                self.send_to_all(m)
                self.top = 0
            else:
                self.put_back(0, m)
                self._busy = True
        else:
            self.n_inst += 1
            return self._make_task(m.content)


    def _release(self):

        assert(self.msgs_ord or self.msgs_unord)

        if self.msgs_ord:
            if self.top in self.msgs_ord:
                disp = self.msgs_ord.pop(self.top)
                self.send_dispatch(disp)

                self.top += 1

                return 1

        elif self.msgs_unord:
            disp = self.msgs_unord.pop()
            self.send_dispatch(disp)
            return 1

        return 0


    def commit(self, response):

        self.n_inst -= 1

        if response.action == 'send':

            # Queue

            priority = response.aux_data

            if type(priority) is int:
                assert(priority >= 0)
                assert(priority not in self.msgs_ord)
                self.msgs_ord[priority] = response.dispatch

            else:
                self.msgs_unord.appendleft(response.dispatch)

            # Send
            if self.is_output_unblocked():
                self._release()

            if self.n_inst == 0:
                self._busy = False

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
        assert(len(inputs) == 1)
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

            cont = comm.Record(response.aux_data)

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
        assert(len(inputs) == 2)
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
            self.put_back(0, comm.Record(response.aux_data))

        else:
            print(response.action, 'is not implemented.')


class MonadicReductor(Box):

    def __init__(self, name, inputs, outputs, core, ordered, segmented):
        assert(len(inputs) == 1)
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
            self.put_back(0, comm.Record(response.aux_data))

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
        for i in self.get_ready_inputs():
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


class Router(Vertex):

    def __init__(self, name, inputs, outputs):
        assert(len(inputs) == 1)
        super(Router, self).__init__(name, inputs, outputs)
        self.ports = deque(self.outputs)

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

        # Update port deque.
        if len(self.ports) != len(self.outputs):
            diff = set(self.outputs) - set(self.ports)
            self.ports.extend(diff)

        self.send_dispatch({self.ports[0]: msgs})
        self.ports.rotate()
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
            if port.channel and (not port.channel.is_space_for(1)):
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

        m = StoreVar('__this__')
        m.set(self.this['msg'])

        self.scope.index['__this__'] = m

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

                if trans.is_else and trans.test():
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

        self.is_else = getattr(condition, 'is_else', False)

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

        result = self.condition.test(self.this['msg'])

        self.local_aliases.update(self.condition.locals)
        self.scope.add_from(self.local_aliases)

        return result

    def test_guard(self):
        return bool(self.guard.compute(self.scope)) if self.guard else True

    #---------------------------------------------------

    def assign(self):

        for act in self.actions['Assign']:
            lhs, rhs = act[1:]
            self.scope[lhs] = self._compute(rhs)

    def send(self):

        dispatch = {}

        for act in self.actions['Send']:
            msg, port = act[1:]

            outcome = self._compute(msg)

            dispatch[port] = dispatch.get(port, []) + [outcome]

        return dispatch

    def goto(self):
        goto_acts = self.actions['Goto']

        if not goto_acts:
            return None

        act = goto_acts[0]
        return act[1]

    #---------------------------------------------------

    def _compute(self, exp):
        assert(hasattr(exp, 'compute'))
        return exp.compute(self.scope)

#------------------------------------------------------------------------------

class Scope:

    def __init__(self, items):

        self.items = []
        self.tmp_items = []

        self.index = {}

        for v in items:

            if not isinstance(v, Variable):
                raise ValueError('Item of a wrong type: %s, Variable expected'
                                 % type(v))

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
            raise IndexError('Name `%s\' is not in the scope' % name)

    def __setitem__(self, name, value):
        if name in self.index:
            # Set value to existing variable.
            self.index[name].set(value)
        else:
            # Create new temporary variable.
            obj = Local(name)
            obj.set(value)
            self.tmp_items.append(obj)
            self.index[name] = obj

    def add_from(self, container):
        if not isinstance(container, dict):
            raise ValueError('add_from() supports only dict containers.')

        else:
            for n, v in container.items():
                self[n] = v

    def __contains__(self, name):
        return name in self.index

#------------------------------------------------------------------------------

class Variable:

    def __init__(self, name):

        if not isinstance(name, str):
            raise TypeError('Variable name must be a string.')

        self.name = name
        self.value = None

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def __repr__(self):
        raise NotImplementedError('Representation is not implemented.')


class Local(Variable):

    def __repr__(self):
        return 'local(%s = %s)' % (self.name, self.value)


class Const(Variable):

    def __init__(self, name, value):
        super(Const, self).__init__(name)
        self.value = value

    def set(self, value):
        raise RuntimeError('Constant `%s\' cannot be changed.' % self.name)

    def __repr__(self):
        return 'const(%s = %s)' % (self.name, self.value)


class StateInt(Variable):

    def __init__(self, name, width, value=0):
        super(StateInt, self).__init__(name)

        if not isinstance(width, int):
            raise TypeError('State variable width must be a positive integer.')

        if width < 1:
            raise ValueError('State variable width must be a positive integer.')

        self.width = width
        self.set(value)

    def set(self, value):

        if not isinstance(value, int):
            raise TypeError('Assignment error for `%s\': value must be integer'
                            % self.name)

        if (- 2 ** (self.width - 1)) <= value <= (2 ** (self.width - 1) - 1):
            self.value = value

        else:
            raise RuntimeError(
                'Assignment error for `%s\': %d is out of range for integer '
                'with bitwidth %d.' % (self.name, value, self.width))

    def __repr__(self):
        return 'state(int%s %s = %s)' % (self.width, self.name, self.value)


class StateEnum(Variable):

    def __init__(self, name, labels, value=0):
        super(StateEnum, self).__init__(name)

        if not isinstance(labels, Sequence) or isinstance(labels, str):
            raise TypeError('Labels must be an iterable container.')

        if not labels:
            raise ValueError('Labels container cannot be empty.')

        for label in labels:
            if type(label) is not str:
                raise ValueError('Label of type `%s\' found, string expected.'
                                 % type(label))

        self.labels = tuple(labels)
        self.label_index = {label: i for i, label in enumerate(labels)}

        self.set(value)

    #----

    def _test_value(self, value):
        return 0 <= value < len(self.labels)

    def _get_int(self, label):

        if label not in self.label_index:
            raise RuntimeError(
                'Error for `%s\': label %s is not defined for the enum'
                % (self.name, label))

        return self.label_index[label]

    def _get_label(self, value=None):

        if value is not None:
            if not self._test_value(value):
                raise RuntimeError(
                    'Error for `%s\': value %s does not correspond to any '
                    'label of enum' % (self.name, value))

            return self.labels[value]

        else:
            assert(self._test_value(self.value))
            return self.labels[self.value]

    #----

    def set(self, value):

        if type(value) is str:
            # Named constant.
            self.value = self._get_int(value)

        elif type(value) is int:
            # Direct integer value.
            self._get_label(value)  # Result is not used, just for typecheck.
            self.value = value

    def __repr__(self):
        return 'state(enum %s = %s)' % (self.name, self._get_label())


class StoreVar(Variable):

    def set(self, value):

        if not isinstance(value, comm.DataMessage):
            raise TypeError(
                'Assignment error for `%s\': value has type `%s\', message '
                'expected.' % (self.name, type(value)))

        self.value = value

    def __repr__(self):
        return 'store(%s = %s)' % (self.name, self.get())
