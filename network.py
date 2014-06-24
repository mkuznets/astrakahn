#!/usr/bin/env python3

import networkx as nx
import re
import components as comp
import communication as comm
from collections import namedtuple


def channel_map(names):
    cmap = {}
    for i in range(len(names)):
        name = names[i]
        if name in cmap:
            cmap[name].append(i)
        else:
            cmap[name] = [i]
    return cmap


def box_spec(category):
    box_tuple = namedtuple("Box", "box n_inputs n_outputs ordered segmentable")

    # Type handling
    cat_re = re.compile('([1-9]\d*)?(T|I|C|P|DO|DU|MO|MS|MU)([1-9]\d*)?')
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
        segmentable = True if cat[1] == 'S' else False

    elif cat == 'C':
        box_class = comp.Consumer
        assert(not n1 and n2)

    elif cat == 'P':
        box_class = comp.Producer
        assert(n1 and not n2)

    else:
        raise ValueError("Wrong box category")

    return box_tuple(box_class, n_inputs, n_outputs, ordered, segmentable)


class Network:

    def __init__(self, name):
        self.network = nx.DiGraph()
        self.global_inputs = {}
        self.global_outputs = {}

        # Wrappers for generic methods operating with global channels.
        self.add_global_inputs = self.add_globals(self.global_inputs)
        self.add_global_outputs = self.add_globals(self.global_outputs)
        self.remove_global_input = self.remove_global(self.global_inputs)
        self.remove_global_output = self.remove_global(self.global_outputs)
        self.rewire_global_inputs = self.rewire_globals(self.global_inputs,
                                                        'set_input')
        self.rewire_global_outputs = self.rewire_globals(self.global_outputs,
                                                         'set_output')

    def add_vertex(self, category, name, inputs, outputs, core, args={}):

        # Forbid identical names in the network
        if name in self.vertices():
            raise ValueError("There's already a box with this name.")

        if type(args) != dict:
            raise ValueError("Wrong box arguments!")

        box_class, n_inputs, n_outputs, ordered, segmentable = box_spec(category)

        if len(inputs) != n_inputs or len(outputs) != n_outputs:
            raise ValueError("Wrong channels definition")

        if (ordered is not None) and (segmentable is not None):
            args['ordered'] = ordered
            args['segmentable'] = segmentable

        box = box_class(n_inputs, n_outputs, core, **args)

        inputs_map = channel_map(inputs)
        outputs_map = channel_map(outputs)

        self.add_global_inputs(name, inputs_map)
        self.add_global_outputs(name, outputs_map)

        # Add node to the graph
        self.network.add_node(name, {'box': box, 'inputs': inputs_map,
                                     'outputs': outputs_map})

    def vertices(self):
        return self.network.nodes()

    def edges(self):
        return self.network.edges()

    def vertex_box(self, v):
        return self.network.node[v]['box']

    def wire(self, src, dst):
        if (type(src) != tuple or type(dst) != tuple) or len(src) != 2 or len(dst) != 2:
            raise ValueError("Wrong wiring arguments.")

        if not self._is_loc_in_graph(src) or not self._is_loc_in_graph(dst):
            raise ValueError("Wrong source or destination.")

        from_vname, from_cname = src
        to_vname, to_cname = dst

        if (from_vname, to_vname) in self.network.edges():
            wires = self.network.edge[from_vname][to_vname]['wires']
        else:
            wires = []

        wires.append((from_cname, to_cname))

        self.network.add_edge(from_vname, to_vname, {'wires': wires})

        self.remove_global_output(from_vname, from_cname)
        self.remove_global_input(to_vname, to_cname)

    def rewire(self):

        for e in self.edges():
            f, t = e
            for (src, dst) in self.network.edge[f][t]['wires']:

                for src_cid in self.network.node[f]['outputs'][src]:
                    for dst_cid in self.network.node[t]['inputs'][dst]:
                        channel = comm.Channel()
                        self.network.node[f]['box'].set_output(src_cid, channel)
                        self.network.node[t]['box'].set_input(dst_cid, channel)

        self.rewire_global_inputs()
        self.rewire_global_outputs()

    def start(self):
        self.rewire()
        for v in self.vertices():
            self.network.node[v]['box'].start()

    def join(self):
        for v in self.vertices():
            self.network.node[v]['box'].join()

    def _is_loc_in_graph(self, pair):
        name, channel = pair
        if name not in self.network.nodes():
            return False
        if channel not in self.network.node[name]['inputs'].keys()\
                and channel not in self.network.node[name]['outputs'].keys():
            return False
        return True

    def add_globals(self, global_map):
        def add_globals_inner(vname, channel_map):
            for cname, cids in channel_map.items():
                name_cid_set = set(zip([vname] * len(cids), cids))
                global_map[cname] = global_map.get(cname, set()) | name_cid_set
        return add_globals_inner

    def remove_global(self, global_map):
        def remove_gloval_inner(vname, cname):
            # Look for the channels with the given name in a given vertex.
            channels_found = set()
            for (v, cid) in global_map[cname]:
                if v == vname:
                    channels_found.add((v, cid))
            # Remove found channels.
            global_map[cname] -= channels_found
            # There are no channels of this name -- delete item from dict.
            if not global_map[cname]:
                del global_map[cname]
        return remove_gloval_inner

    def rewire_globals(self, global_map, method):
        def rewire_globals_inner():
            for (cname, vlist) in global_map.items():
                for vname, cid in vlist:
                    channel = comm.Channel()
                    setter = getattr(self.network.node[vname]['box'], method)
                    setter(cid, channel)
        return rewire_globals_inner

    def debug_status(self):
        print("Vertices:")
        for v in self.vertices():
            print("\t", v, self.vertex_box(v))

        print("\nWires:")
        for v in self.edges():
            f, t = v
            for (src, dst) in self.network.edge[f][t]['wires']:
                print("\t",
                      f + "[" + str(src) + "] ->",
                      t + "[" + str(dst) + "]")

        print("\nGlobal inputs:")
        for (cname, blist) in self.global_inputs.items():
            for b, cid in blist:
                print("\t", b + "[" + cname + "]")

        print("\nGlobal outputs:")
        for (cname, blist) in self.global_outputs.items():
            for b, cid in blist:
                print("\t", b + "[" + cname + "]")

#class morphism:
#    @staticmethod
#    def split(category):
#        def wrap(f):
#            f.spec = box_spec(category)
#            return f
#        return wrap
#
#    def map(f, category):
#        pass
#
#
#class Solver():
#    @morphism.split("1I")
#    def particle_partition(self, a, b):
#        print(a, b)
#
#    @morphism.map("1T")
#    def foo(self, a):
#        pass
#
#
#S = Solver()
#print(S.particle_partition.__code__.co_varnames)
#
#quit()
