#-----------------------------------------------------------------
# ** ATTENTION **
# This code was automatically generated from the file:
# ast/net_ast.cfg
#
# Do not modify it directly. Modify the configuration file and
# run the generator again.
# ** ** *** ** **
#
# Node library for syncroniser AST.
#
# Copyright (C) 2014, Max Kuznetsov
# License: BSD
#-----------------------------------------------------------------


import sys


class Node(object):
    """ Abstract base class for AST nodes.
    """
    def children(self):
        """ A sequence of all children that are Nodes
        """
        pass

    def show(self, buf=sys.stdout, offset=0, attrnames=False, nodenames=False, showcoord=False, _my_node_name=None):
        """ Pretty print the Node and all its attributes and
            children (recursively) to a buffer.

            buf:
                Open IO buffer into which the Node is printed.

            offset:
                Initial offset (amount of leading spaces)

            attrnames:
                True if you want to see the attribute names in
                name=value pairs. False to only see the values.

            nodenames:
                True if you want to see the actual node names
                within their parents.

            showcoord:
                Do you want the coordinates of each Node to be
                displayed.
        """
        lead = ' ' * offset
        if nodenames and _my_node_name is not None:
            buf.write(lead + self.__class__.__name__+ ' <' + _my_node_name + '>: ')
        else:
            buf.write(lead + self.__class__.__name__+ ': ')

        if self.attr_names:
            if attrnames:
                nvlist = [(n, getattr(self,n)) for n in self.attr_names]
                attrstr = ', '.join('%s=%s' % nv for nv in nvlist)
            else:
                vlist = [getattr(self, n) for n in self.attr_names]
                attrstr = ', '.join('%s' % v for v in vlist)
            buf.write(attrstr)

        if showcoord:
            buf.write(' (at %s)' % self.coord)
        buf.write('\n')

        for (child_name, child) in self.children(expand=True):
            child.show(
                buf,
                offset=offset + 2,
                attrnames=attrnames,
                nodenames=nodenames,
                showcoord=showcoord,
                _my_node_name=child_name)


class NodeVisitor(object):

    def generic_visit(self, node, children):
        pass

    def traverse(self, node):

        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        children = {}

        if visitor.__doc__ != 'final':
            # Skip the children

            for c_name, c in node.children():
                if type(c) == list:
                    outcome = [self.traverse(i) for i in c]
                else:
                    outcome = self.traverse(c)

                children[c_name] = outcome

        return visitor(node, children) if visitor else None


class Net(Node):
    def __init__(self, is_pure, name, inputs, outputs, decls, wiring, coord=None):
        self.is_pure = is_pure
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.decls = decls
        self.wiring = wiring
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.inputs is not None: nodelist.append(("inputs", self.inputs))
        if self.outputs is not None: nodelist.append(("outputs", self.outputs))
        if self.decls is not None: nodelist.append(("decls", self.decls))
        if self.wiring is not None: nodelist.append(("wiring", self.wiring))
        return tuple(nodelist)

    attr_names = ('is_pure','name',)

class PortList(Node):
    def __init__(self, ports, coord=None):
        self.ports = ports
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if expand:
            for i, child in enumerate(self.ports or []):
                nodelist.append(("ports[%d]" % i, child))
        else:
            nodelist.append(("ports", list(self.ports) or []))
        return tuple(nodelist)

    attr_names = ()

class DeclList(Node):
    def __init__(self, decls, coord=None):
        self.decls = decls
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if expand:
            for i, child in enumerate(self.decls or []):
                nodelist.append(("decls[%d]" % i, child))
        else:
            nodelist.append(("decls", list(self.decls) or []))
        return tuple(nodelist)

    attr_names = ()

class SynchTab(Node):
    def __init__(self, labels, sync, coord=None):
        self.labels = labels
        self.sync = sync
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.sync is not None: nodelist.append(("sync", self.sync))
        return tuple(nodelist)

    attr_names = ('labels',)

class Synchroniser(Node):
    def __init__(self, name, configs, coord=None):
        self.name = name
        self.configs = configs
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('name','configs',)

class Morphism(Node):
    def __init__(self, split, map, join, coord=None):
        self.split = split
        self.map = map
        self.join = join
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('split','map','join',)

class BinaryOp(Node):
    def __init__(self, op, left, right, coord=None):
        self.op = op
        self.left = left
        self.right = right
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.left is not None: nodelist.append(("left", self.left))
        if self.right is not None: nodelist.append(("right", self.right))
        return tuple(nodelist)

    attr_names = ('op',)

class UnaryOp(Node):
    def __init__(self, op, operand, coord=None):
        self.op = op
        self.operand = operand
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.operand is not None: nodelist.append(("operand", self.operand))
        return tuple(nodelist)

    attr_names = ('op',)

class Vertex(Node):
    def __init__(self, inputs, outputs, name, coord=None):
        self.inputs = inputs
        self.outputs = outputs
        self.name = name
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('inputs','outputs','name',)

class ID(Node):
    def __init__(self, value, coord=None):
        self.value = value
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('value',)

class NUMBER(Node):
    def __init__(self, value, coord=None):
        self.value = value
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('value',)

