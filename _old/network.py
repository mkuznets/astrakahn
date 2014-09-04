#!/usr/bin/env python3

import networkx as nx
import re
import components as comp
import communication as comm
from collections import namedtuple
import copy

Port = namedtuple("Port", "vname side cid")


def box_spec(category):
    box_tuple = namedtuple("Box", "box n_inputs n_outputs ordered segmentable")

    # Type handling
    cat_re = re.compile('([1-9]\d*)?(T|I|C|P|R|S|DO|DU|MO|MS|MU)([1-9]\d*)?')
    parse = cat_re.findall(category)

    if not parse:
        raise ValueError("Wrong box category")

    n1, cat, n2 = parse[0]
    ordered = None
    segmentable = None

    n_outputs = int(n1) if n1 else 0
    n_inputs = (2 if cat[0] == 'D' else 1) if n1 else int(n2)

    # Assign box class
    if cat == 'T':
        box_class = comp.Transductor
        assert(n1 and not n2)

    elif cat == 'I':
        box_class = comp.Inductor
        assert(n1 and not n2)

    elif cat[0] == 'D' or cat[0] == 'M':
        assert(n1 and not n2)
        box_class = comp.Reductor
        ordered = True if cat[1] != 'U' else False
        segmentable = True if cat[1] == 'S' or cat[1] == 'U' else False

    elif cat == 'C':
        box_class = comp.Consumer
        assert(not n1 and n2)

    elif cat == 'P':
        box_class = comp.Producer
        assert(n1 and not n2)

    elif cat == 'R':
        box_class = comp.Repeater
        assert(n1 and n2)
        n_inputs, n_outputs = int(n2), int(n1)

    elif cat == 'S':
        box_class = comp.Synchroniser
        assert(n1 and n2)
        n_inputs, n_outputs = int(n2), int(n1)

    else:
        raise ValueError("Wrong box category")

    return box_tuple(box_class, n_inputs, n_outputs, ordered, segmentable)


class Network:

    def __init__(self, name):
        self.network = nx.DiGraph()
        self.channels = {'in': {}, 'out': {}}

        self.wires = {}
        self.wid_cnt = 0
        self.rcnt = 0

    ## Getters:
    ##

    def vertices(self):
        return self.network.nodes()

    def edges(self):
        return self.network.edges()

    def vertex_box(self, v):
        return self.network.node[v]['box']

    def get_wire_id(self, port):
        self.is_port(port)
        return self.network.node[port.vname][port.side][port.cid]

    def set_wire_id(self, port, wid):
        self.is_port(port)
        self.network.node[port.vname][port.side][port.cid] = wid

    def is_port(self, port):
        if port.vname not in self.vertices():
            raise ValueError("Wrong vertex name.")
        n_channels = len(self.network.node[port.vname][port.side])
        if port.cid < 0 or n_channels < (port.cid + 1):
            raise ValueError("Wrong channel id or side.")

    ## Network builders
    ##

    def add_vertex(self, category, name, inputs, outputs, **args):
        # Forbid identical names in the network
        if name in self.vertices():
            raise ValueError("There's already a box with this name:", name)

        box_class, n_inputs, n_outputs, ordered, segmentable = box_spec(category)

        if len(inputs) != n_inputs or len(outputs) != n_outputs:
            raise ValueError("Wrong channels definition")

        if (ordered is not None) and (segmentable is not None):
            args['ordered'] = ordered
            args['segmentable'] = segmentable

        box = box_class(n_inputs, n_outputs, **args)

        for side in ['in', 'out']:
            for cid, cname in enumerate(inputs if side == 'in' else outputs):
                if cname in self.channels[side]:
                    self.channels[side][cname].append(Port(name, side, cid))
                else:
                    self.channels[side][cname] = [Port(name, side, cid)]

        # Add node to the graph
        self.network.add_node(name, {'box': box, 'in': [None]*n_inputs,
                                     'out': [None]*n_outputs})

    def add_wire(self, src, dst):

        src = Port(src[0], 'out', src[1])
        dst = Port(dst[0], 'in', dst[1])

        wid_in = self.get_wire_id(dst)
        wid_out = self.get_wire_id(src)

        # Both ports are ports are connected to some wires (not necessarily to
        # the same one)
        if (wid_in is not None) and (wid_out is not None):
            if wid_in == wid_out:
                return

            for side in ['in', 'out']:
                for p in self.wires[wid_in][side]:
                    self.wires[wid_out][side].append(p)

            del self.wires[wid_in]
            self.wid_cnt -= 1

        elif (wid_in is None) and (wid_out is None):
            self.set_wire_id(src, self.wid_cnt)
            self.set_wire_id(dst, self.wid_cnt)

            if self.wid_cnt not in self.wires:
                self.wires[self.wid_cnt] = {'in': [], 'out': []}
            self.wires[self.wid_cnt]['in'].append(dst)
            self.wires[self.wid_cnt]['out'].append(src)

            self.wid_cnt += 1

        elif (wid_in is not None) or (wid_out is not None):
            wid = wid_in if (wid_in is not None) else wid_out
            self.set_wire_id(src, wid)
            self.set_wire_id(dst, wid)

            if wid_in:
                self.wires[wid_in]['in'].append(dst)
            elif wid_out:
                self.wires[wid_out]['out'].append(src)

    def flatten_wiring(self):
        wids = list(self.wires.keys())

        for wid in wids:
            ports = self.wires[wid]

            if len(ports['in']) > 1 or len(ports['out']) > 1:
                # Multiconnection is transformed to repeater.
                ni = len(ports['in'])
                no = len(ports['out'])

                for side in ['in', 'out']:
                    for p in ports[side]:
                        self.network.node[p.vname][p.side][p.cid] = None

                del self.wires[wid]

                cat = str(no) + 'R' + str(ni)
                name = 'rep_' + str(self.rcnt)
                self.rcnt += 1
                self.add_vertex(cat, name, ['_' + str(i) for i in range(ni)],
                                ['_' + str(i) for i in range(no)])

                # Connect inputs of repeater.
                for i, p in enumerate(ports['out']):
                    self.add_wire((p.vname, p.cid), (name, i))
                # Connect outputs of repeater.
                for i, p in enumerate(ports['in']):
                    self.add_wire((name, i), (p.vname, p.cid))

    ## Network operators.
    ##

    def serial_composition(self, net):
        self.composition(net, wiring=True)

    def parallel_composition(self, net):
        self.composition(net, wiring=False)

    def composition(self, net, wiring=False):
        if wiring:
            # Common channel names (outputs of `self' and inputs of `net').
            common = set(self.channels['out']) & set(net.channels['in'])

        wires = copy.copy(net.wires)
        self.network = nx.union(self.network, net.network)

        # Wire merging and renaming: increase all wire ids from `net' to
        # prevent collision.
        for wid, ports in wires.items():
            self.wires[wid + self.wid_cnt] = ports
            for p in ports['in'] + ports['out']:
                self.set_wire_id(p, self.get_wire_id(p) + self.wid_cnt)
        self.wid_cnt = max(self.wires) + 1

        if wiring:
            # Create connection between identically named channels.
            for cname in common:
                # Get global ports by the channel name.
                ports_dst = [p for p in net.channels['in'][cname]
                             if self.get_wire_id(p) is None]
                ports_src = [p for p in self.channels['out'][cname]
                             if self.get_wire_id(p) is None]

                for ps in ports_src:
                    for pd in ports_dst:
                        self.add_wire((ps.vname, ps.cid), (pd.vname, pd.cid))

        # Merge channels.
        for side in ['in', 'out']:
            for cname, ports in net.channels[side].items():
                if cname in self.channels[side]:
                    self.channels[side][cname] += ports
                else:
                    self.channels[side][cname] = ports

    def wire_physical(self):
        # All wires must be single-producer-single-consumer.
        self.flatten_wiring()

        # Assign queues to wires.
        for wid, ports in self.wires.items():
            assert(len(ports['in']) == 1 and len(ports['out']) == 1)
            p_in = ports['in'][0]
            p_out = ports['out'][0]

            channel = comm.Channel()
            self.vertex_box(p_in.vname).set_input(p_in.cid, channel)
            self.vertex_box(p_out.vname).set_output(p_out.cid, channel)

        # Assign queues to global inputs and outputs.
        for side in ['in', 'out']:
            for (cname, ports) in self.channels[side].items():
                for p in ports:
                    if self.get_wire_id(p) is None:
                        channel = comm.Channel()
                        if side == 'in':
                            self.vertex_box(p.vname).set_input(p.cid, channel)
                        else:
                            self.vertex_box(p.vname).set_output(p.cid, channel)

    def start(self):
        self.wire_physical()
        for v in self.vertices():
            self.vertex_box(v).start()

    def join(self):
        for v in self.vertices():
            self.vertex_box(v).join()

    ## Debug.
    ##

    def debug_status(self):
        print("Vertices:")
        for v in self.vertices():
            print("\t", v, self.vertex_box(v))

        print("\nInputs:")
        for (cname, ports) in self.channels['in'].items():
            for p in ports:
                print("\t", p.vname + "[" + cname + ", " + str(p.cid) + "]")

        print("\nOutputs:")
        for (cname, ports) in self.channels['out'].items():
            for p in ports:
                print("\t", p.vname + "[" + cname + ", " + str(p.cid) + "]")

        print("\nWires:")

        for w in self.wires.items():
            print(w)

        for v in self.edges():
            f, t = v
            for (src, dst, args) in self.network.edge[f][t]['wires']:
                print("\t",
                      f + str(tuple(src)) + " ->",
                      t + str(tuple(dst)) + "")

        print("\nGlobal inputs:")
        for (cname, ports) in self.channels['in'].items():
            for p in ports:
                if self.get_wire_id(p) is None:
                    print("\t", p.vname + "[" + cname + ", " + str(p.cid) + "]")

        print("\nGlobal outputs:")
        for (cname, ports) in self.channels['out'].items():
            for p in ports:
                if self.get_wire_id(p) is None:
                    print("\t", p.vname + "[" + cname + ", " + str(p.cid) + "]")


if __name__ == "__main__":

    N = Network('test')
    N.add_vertex("1I", "A", ['i00'], ['o00'], core=print)
    N.add_vertex("1T", "B", ['i10'], ['o10'], core=print)
    N.add_vertex("1T", "C", ['i20'], ['o20'], core=print)
    N.add_vertex("1T", "D", ['i30'], ['o30'], core=print)

    N.add_wire(('A', 0), ('B', 0))
    N.add_wire(('C', 0), ('D', 0))
    N.add_wire(('A', 0), ('D', 0))

    P = Network('test2')
    P.add_vertex("1I", "I", ['o30'], ['gen'], core=print)
    P.add_vertex("1T", "T", ['out'], ['ready'], core=print)
    P.add_vertex("1MU", "R", ['i'], ['r'], core=print)
    P.add_wire(('I', 0), ('T', 0))
    P.add_wire(('T', 0), ('R', 0))

    #N.serial_composition(P)
    N.parallel_composition(P)

    N.flatten_wiring()
    N.wire_physical()
    N.debug_status()
