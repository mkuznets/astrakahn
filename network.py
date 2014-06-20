#!/usr/bin/env python3

import networkx as nx
import re
import components as comp
import collections

def map_inverse(old_map):
    inv_map = {}
    for k, v in old_map.items():
        inv_map[v] = inv_map.get(v, [])
        inv_map[v].append(k)
    return inv_map


def map_merge(a, b):
    merged_map = {}
    for (name, value) in b.items():
        merged_map[name] = a.get(name, [])
        merged_map[name] += value
    for k in a.keys():
        if k not in merged_map:
            merged_map[k] = a[k]
    return merged_map


def box_spec(category):
    box_tuple = collections.namedtuple("Box", "box n_inputs n_outputs")

    # Type handling
    category_regexp = re.compile('([1-9]\d*)(T|I|G|DO|DU|MO|MS|MU)')
    category_parse = category_regexp.findall(category)

    if not category_parse:
        raise ValueError("Wrong box category")

    box_category = category_parse[0][1]

    n_outputs = int(category_parse[0][0])
    n_inputs = 2 if box_category[0] == 'D' else 1

    # Assign box class
    if box_category == 'T':
        box_class = comp.Transductor
    elif box_category == 'I':
        box_class = comp.Inductor
    elif box_category == 'G':
        box_class = comp.Generator
    elif box_category[0] == 'D' or box_category[0] == 'M':
        box_class = comp.Reductor
    else:
        raise ValueError("Wrong box category")

    return box_tuple(box_class, n_inputs, n_outputs)


class Network:

    def __init__(self, name):
        self.network = nx.Graph()
        self.global_inputs = {}
        self.global_outputs = {}

    def add_node(self, category, name, channels, core, passport, args=None):

        # Forbid identical names in the network
        if name in self.network.nodes():
            raise ValueError("There's already a box with this name.")

        box = BoxWrapper(category, name, channels, core, passport, args)

        # Inverse mapping of channels to be able to get channels by name
        inputs = map_inverse(box.inputs)
        outputs = map_inverse(box.outputs)

        # Add channels to global ins/outs
        self._add_global_channels(name, inputs, outputs)

        # Add node to the graph
        self.network.add_node(name, {'box': box, 'inputs': inputs,
                                     'outputs': outputs})

    def remove_node(self, label):
        pass

    def nodes(self):
        return self.network.nodes()

    def wire(self, src, dst):
        if (type(src) != tuple or type(dst) != tuple) or len(src) != 2 or len(dst) != 2:
            raise ValueError("Wrong wiring arguments.")

        if not self._is_loc_in_graph(src) or not self._is_loc_in_graph(dst):
            raise ValueError("Wrong source or destination.")

        from_name, from_channel = src
        to_name, to_channel = dst

        self.network.add_edge(from_name, to_name, {'src': from_channel, 'dst': to_channel})

        self._remove_global_channels(from_name, from_channel)
        self._remove_global_channels(to_name, to_channel)

    def _is_loc_in_graph(self, pair):
        name, channel = pair
        if name not in self.network.nodes():
            return False
        if channel not in self.network.node[name]['inputs'].keys()\
                and channel not in self.network.node[name]['outputs'].keys():
            return False
        return True

    def _add_global_channels(self, node_name, inputs, outputs):
        merge = lambda x, y: map_merge(x, {k: [tuple(v + [node_name])] for (k, v) in y.items()})
        self.global_inputs = merge(self.global_inputs, inputs)
        self.global_outputs = merge(self.global_outputs, outputs)

    def _remove_global_channels(self, node_name, channel_name):
        delete_from = self.global_inputs if self._is_input(node_name, channel_name) else self.global_outputs

        for channel in delete_from[channel_name]:
            if channel[1] == node_name:
                delete_from[channel_name].remove(channel)

    def _is_input(self, node_name, channel_name):
        if channel_name not in self.network.node[node_name]['inputs']:
            return False
        return True

    def parallel_union(self):
        pass

    def serial_union(self):
        pass




class BoxWrapper:

    def __init__(self, category, name, channels, core, passport, args):


        self._box_class, self.n_inputs, self.n_outputs = box_spec(category)

        # Default names
        self.inputs = {i: '_' + str(i) for i in range(self.n_inputs)}
        self.outputs = {i: '_' + str(i) for i in range(self.n_outputs)}

        # Check for consistency of channels definition
        if type(channels[0]) == tuple and self.n_inputs < len(channels[0]) \
                or type(channels[1]) == tuple and self.n_outputs < len(channels[1]):
            raise ValueError("Wrong channels definition")

        # Set channel names
        self._rename_channels(channels)

        # Box internals
        self.function = core
        self.passport = passport

        self.box = None

    def initiate(self):
        if self.box is None:
            self.box = self._box_class(n_inputs=self.n_inputs,
                                       n_outputs=self.n_outputs,
                                       core=self.core, passport=self.passport)
            print("Info: Box has been initiated")
        else:
            print("Warning: The box has already been initiated")

    def _get_constructor(self, box_type):
        if box_type == 'T':
            return comp.Transductor
        elif box_type == 'I':
            return comp.Inductor
        elif box_type[0] == 'D' or box_type[0] == 'M':
                return comp.Reductor

    def _rename_channels(self, channel_names):

        # Loop over 2-tuple with input/output names
        for i in range(2):

            # Input/output channel selector
            names = channel_names[i]
            if i == 0:
                n = self.n_inputs
                channel_list = self.inputs
            else:
                n = self.n_outputs
                channel_list = self.outputs

            # Get names from {old-name: new-name}-dictionary
            if type(names) == dict:
                for i in range(n):
                    subname = '_' + str(i)
                    if subname in names:
                        channel_list[i] = str(names[subname])

            # Get names from enumarative tuple
            elif type(names) == tuple:
                for i in range(len(names)):
                    channel_list[i] = str(names[i])

            # If the box has the only input or output, it's possible to pass
            # a string instead of dict/tuple
            elif type(names) == str:
                # Consider a string to be a 1-tuple:
                channel_list[0] = names
            else:
                raise ValueError("Wrong format of channel names")


class morphism:
    @staticmethod
    def split(category):
        def wrap(f):
            f.spec = box_spec(category)
            return f
        return wrap

    def map(f, category):
        pass


class Solver():
    @morphism.split("1I")
    def particle_partition(self, a, b):
        print(a, b)

    @morphism.map("1T")
    def foo(self, a):
        pass






S = Solver()
print(S.particle_partition.__code__.co_varnames)

quit()

if __name__ == '__main__':

    P = Network("test_network")
    P.add_node("1I", "AdjNodes", ('input', 'text'),  (lambda x: x*x), "")
    P.add_node("2T", "NewNodes", ('input', ('text', 'untext')),  (lambda x: x*x), "")

    P.wire(('AdjNodes', 'text'), ('NewNodes', 'input'))

    print(P.network.edges())
    print(P.global_inputs)
    print(P.global_outputs)
