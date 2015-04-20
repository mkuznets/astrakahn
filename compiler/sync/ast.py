#-----------------------------------------------------------------
# ** ATTENTION **
# This code was automatically generated from the file:
# ast/sync_ast.cfg
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
        raise NotImplementedError('generic_visit is not implemented')

    def traverse(self, node):
        """ Called if no explicit visitor function exists for a
            node. Implements preorder visiting of the node.
        """

        children = {}

        for c_name, c in node.children():
            if type(c) == list:
                outcome = [self.traverse(i) for i in c]
            else:
                outcome = self.traverse(c)

            children[c_name] = outcome

        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, children) if visitor else None


class Sync(Node):
    def __init__(self, name, inputs, outputs, decls, states, configs, coord=None):
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.decls = decls
        self.states = states
        self.configs = configs
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if self.inputs is not None: nodelist.append(("inputs", self.inputs))
        if self.outputs is not None: nodelist.append(("outputs", self.outputs))
        if self.decls is not None: nodelist.append(("decls", self.decls))
        if self.states is not None: nodelist.append(("states", self.states))
        return tuple(nodelist)

    attr_names = ('configs',)

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

class Port(Node):
    def __init__(self, name, depth_exp, coord=None):
        self.name = name
        self.depth_exp = depth_exp
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if self.depth_exp is not None: nodelist.append(("depth_exp", self.depth_exp))
        return tuple(nodelist)

    attr_names = ()

class DepthExp(Node):
    def __init__(self, depth, sign, shift, coord=None):
        self.depth = depth
        self.sign = sign
        self.shift = shift
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.depth is not None: nodelist.append(("depth", self.depth))
        if self.shift is not None: nodelist.append(("shift", self.shift))
        return tuple(nodelist)

    attr_names = ('sign',)

class DepthNone(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self, expand=False):
        return ()

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

class StoreVar(Node):
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        return tuple(nodelist)

    attr_names = ()

class StateVar(Node):
    def __init__(self, name, type, value, coord=None):
        self.name = name
        self.type = type
        self.value = value
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if self.type is not None: nodelist.append(("type", self.type))
        if self.value is not None: nodelist.append(("value", self.value))
        return tuple(nodelist)

    attr_names = ()

class IntType(Node):
    def __init__(self, size, coord=None):
        self.size = size
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.size is not None: nodelist.append(("size", self.size))
        return tuple(nodelist)

    attr_names = ()

class EnumType(Node):
    def __init__(self, labels, coord=None):
        self.labels = labels
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if expand:
            for i, child in enumerate(self.labels or []):
                nodelist.append(("labels[%d]" % i, child))
        else:
            nodelist.append(("labels", list(self.labels) or []))
        return tuple(nodelist)

    attr_names = ()

class StateList(Node):
    def __init__(self, states, coord=None):
        self.states = states
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if expand:
            for i, child in enumerate(self.states or []):
                nodelist.append(("states[%d]" % i, child))
        else:
            nodelist.append(("states", list(self.states) or []))
        return tuple(nodelist)

    attr_names = ()

class State(Node):
    def __init__(self, name, trans_orders, coord=None):
        self.name = name
        self.trans_orders = trans_orders
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        if expand:
            for i, child in enumerate(self.trans_orders or []):
                nodelist.append(("trans_orders[%d]" % i, child))
        else:
            nodelist.append(("trans_orders", list(self.trans_orders) or []))
        return tuple(nodelist)

    attr_names = ()

class TransOrder(Node):
    def __init__(self, trans_stmt, coord=None):
        self.trans_stmt = trans_stmt
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if expand:
            for i, child in enumerate(self.trans_stmt or []):
                nodelist.append(("trans_stmt[%d]" % i, child))
        else:
            nodelist.append(("trans_stmt", list(self.trans_stmt) or []))
        return tuple(nodelist)

    attr_names = ()

class Trans(Node):
    def __init__(self, port, condition, guard, actions, coord=None):
        self.port = port
        self.condition = condition
        self.guard = guard
        self.actions = actions
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.port is not None: nodelist.append(("port", self.port))
        if self.condition is not None: nodelist.append(("condition", self.condition))
        if self.guard is not None: nodelist.append(("guard", self.guard))
        if expand:
            for i, child in enumerate(self.actions or []):
                nodelist.append(("actions[%d]" % i, child))
        else:
            nodelist.append(("actions", list(self.actions) or []))
        return tuple(nodelist)

    attr_names = ()

class CondSegmark(Node):
    def __init__(self, depth, coord=None):
        self.depth = depth
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.depth is not None: nodelist.append(("depth", self.depth))
        return tuple(nodelist)

    attr_names = ()

class CondDataMsg(Node):
    def __init__(self, choice, labels, tail, coord=None):
        self.choice = choice
        self.labels = labels
        self.tail = tail
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.choice is not None: nodelist.append(("choice", self.choice))
        if self.tail is not None: nodelist.append(("tail", self.tail))
        if expand:
            for i, child in enumerate(self.labels or []):
                nodelist.append(("labels[%d]" % i, child))
        else:
            nodelist.append(("labels", list(self.labels) or []))
        return tuple(nodelist)

    attr_names = ()

class CondEmpty(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self, expand=False):
        return ()

    attr_names = ()

class CondElse(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self, expand=False):
        return ()

    attr_names = ()

class Assign(Node):
    def __init__(self, lhs, rhs, coord=None):
        self.lhs = lhs
        self.rhs = rhs
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.lhs is not None: nodelist.append(("lhs", self.lhs))
        if self.rhs is not None: nodelist.append(("rhs", self.rhs))
        return tuple(nodelist)

    attr_names = ()

class DataExp(Node):
    def __init__(self, items, coord=None):
        self.items = items
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if expand:
            for i, child in enumerate(self.items or []):
                nodelist.append(("items[%d]" % i, child))
        else:
            nodelist.append(("items", list(self.items) or []))
        return tuple(nodelist)

    attr_names = ()

class ItemThis(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self, expand=False):
        return ()

    attr_names = ()

class ItemVar(Node):
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        return tuple(nodelist)

    attr_names = ()

class ItemExpand(Node):
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.name is not None: nodelist.append(("name", self.name))
        return tuple(nodelist)

    attr_names = ()

class ItemPair(Node):
    def __init__(self, label, value, coord=None):
        self.label = label
        self.value = value
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.label is not None: nodelist.append(("label", self.label))
        if self.value is not None: nodelist.append(("value", self.value))
        return tuple(nodelist)

    attr_names = ()

class Send(Node):
    def __init__(self, msg, port, coord=None):
        self.msg = msg
        self.port = port
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.msg is not None: nodelist.append(("msg", self.msg))
        if self.port is not None: nodelist.append(("port", self.port))
        return tuple(nodelist)

    attr_names = ()

class MsgSegmark(Node):
    def __init__(self, depth, coord=None):
        self.depth = depth
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.depth is not None: nodelist.append(("depth", self.depth))
        return tuple(nodelist)

    attr_names = ()

class MsgData(Node):
    def __init__(self, choice, data_exp, coord=None):
        self.choice = choice
        self.data_exp = data_exp
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if self.choice is not None: nodelist.append(("choice", self.choice))
        if self.data_exp is not None: nodelist.append(("data_exp", self.data_exp))
        return tuple(nodelist)

    attr_names = ()

class MsgNil(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self, expand=False):
        return ()

    attr_names = ()

class Goto(Node):
    def __init__(self, states, coord=None):
        self.states = states
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        if expand:
            for i, child in enumerate(self.states or []):
                nodelist.append(("states[%d]" % i, child))
        else:
            nodelist.append(("states", list(self.states) or []))
        return tuple(nodelist)

    attr_names = ()

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

class TERM(Node):
    def __init__(self, value, coord=None):
        self.value = value
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('value',)

class IntExp(Node):
    def __init__(self, exp, args, terms, coord=None):
        self.exp = exp
        self.args = args
        self.terms = terms
        self.coord = coord

    def children(self, expand=False):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('exp','args','terms',)

