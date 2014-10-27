#-----------------------------------------------------------------
# ** ATTENTION **
# This code was automatically generated from the file:
# _sync_ast.cfg
#
# Do not modify it directly. Modify the configuration file and
# run the generator again.
# ** ** *** ** **
#
# AST Node classes.
#
# Copyright (C) 2008-2013, Eli Bendersky
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

        for (child_name, child) in self.children():
            child.show(
                buf,
                offset=offset + 2,
                attrnames=attrnames,
                nodenames=nodenames,
                showcoord=showcoord,
                _my_node_name=child_name)


class NodeVisitor(object):
    """ A base NodeVisitor class for visiting c_ast nodes.
        Subclass it and define your own visit_XXX methods, where
        XXX is the class name you want to visit with these
        methods.

        For example:

        class ConstantVisitor(NodeVisitor):
            def __init__(self):
                self.values = []

            def visit_Constant(self, node):
                self.values.append(node.value)

        Creates a list of values of all the constant nodes
        encountered below the given node. To use it:

        cv = ConstantVisitor()
        cv.visit(node)

        Notes:

        *   generic_visit() will be called for AST nodes for which
            no visit_XXX method was defined.
        *   The children of nodes for which a visit_XXX was
            defined will not be visited - if you need this, call
            generic_visit() on the node.
            You can use:
                NodeVisitor.generic_visit(self, node)
        *   Modeled after Python's own AST visiting facilities
            (the ast module of Python 3.0)
    """
    def visit(self, node):
        """ Visit a node.
        """
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """ Called if no explicit visitor function exists for a
            node. Implements preorder visiting of the node.
        """
        for c_name, c in node.children():
            self.visit(c)


class Sync(Node):
    def __init__(self, name, macros, inputs, outputs, decls, states, coord=None):
        self.name = name
        self.macros = macros
        self.inputs = inputs
        self.outputs = outputs
        self.decls = decls
        self.states = states
        self.coord = coord

    def children(self):
        nodelist = []
        if self.macros is not None: nodelist.append(("macros", self.macros))
        if self.inputs is not None: nodelist.append(("inputs", self.inputs))
        if self.outputs is not None: nodelist.append(("outputs", self.outputs))
        if self.decls is not None: nodelist.append(("decls", self.decls))
        if self.states is not None: nodelist.append(("states", self.states))
        return tuple(nodelist)

    attr_names = ('name',)

class Macros(Node):
    def __init__(self, macros, coord=None):
        self.macros = macros
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.macros or []):
            nodelist.append(("macros[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ()

class PortList(Node):
    def __init__(self, ports, coord=None):
        self.ports = ports
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.ports or []):
            nodelist.append(("ports[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ()

class Port(Node):
    def __init__(self, name, depth, coord=None):
        self.name = name
        self.depth = depth
        self.coord = coord

    def children(self):
        nodelist = []
        if self.depth is not None: nodelist.append(("depth", self.depth))
        return tuple(nodelist)

    attr_names = ('name',)

class DepthExp(Node):
    def __init__(self, depth, shift, coord=None):
        self.depth = depth
        self.shift = shift
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('depth','shift',)

class DepthNone(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    attr_names = ()

class DeclList(Node):
    def __init__(self, decls, coord=None):
        self.decls = decls
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.decls or []):
            nodelist.append(("decls[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ()

class StoreVar(Node):
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('name',)

class StateVar(Node):
    def __init__(self, name, type, coord=None):
        self.name = name
        self.type = type
        self.coord = coord

    def children(self):
        nodelist = []
        if self.type is not None: nodelist.append(("type", self.type))
        return tuple(nodelist)

    attr_names = ('name',)

class IntType(Node):
    def __init__(self, size, coord=None):
        self.size = size
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('size',)

class EnumType(Node):
    def __init__(self, labels, coord=None):
        self.labels = labels
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.labels or []):
            nodelist.append(("labels[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ()

class StateList(Node):
    def __init__(self, states, coord=None):
        self.states = states
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.states or []):
            nodelist.append(("states[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ()

class State(Node):
    def __init__(self, name, trans_scopes, coord=None):
        self.name = name
        self.trans_scopes = trans_scopes
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.trans_scopes or []):
            nodelist.append(("trans_scopes[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ('name',)

class TransScope(Node):
    def __init__(self, trans_stmt, coord=None):
        self.trans_stmt = trans_stmt
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.trans_stmt or []):
            nodelist.append(("trans_stmt[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ()

class Trans(Node):
    def __init__(self, port, condition, guard, actions, coord=None):
        self.port = port
        self.condition = condition
        self.guard = guard
        self.actions = actions
        self.coord = coord

    def children(self):
        nodelist = []
        if self.condition is not None: nodelist.append(("condition", self.condition))
        if self.guard is not None: nodelist.append(("guard", self.guard))
        for i, child in enumerate(self.actions or []):
            nodelist.append(("actions[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ('port',)

class CondSegmark(Node):
    def __init__(self, depth, coord=None):
        self.depth = depth
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('depth',)

class CondDataMsg(Node):
    def __init__(self, choice, labels, tail, coord=None):
        self.choice = choice
        self.labels = labels
        self.tail = tail
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.labels or []):
            nodelist.append(("labels[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ('choice','tail',)

class CondEmpty(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    attr_names = ()

class CondElse(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    attr_names = ()

class Assign(Node):
    def __init__(self, lhs, rhs, coord=None):
        self.lhs = lhs
        self.rhs = rhs
        self.coord = coord

    def children(self):
        nodelist = []
        if self.rhs is not None: nodelist.append(("rhs", self.rhs))
        return tuple(nodelist)

    attr_names = ('lhs',)

class IntExp(Node):
    def __init__(self, exp, coord=None):
        self.exp = exp
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('exp',)

class DataExp(Node):
    def __init__(self, items, coord=None):
        self.items = items
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.items or []):
            nodelist.append(("items[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ()

class ItemThis(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    attr_names = ()

class ItemVar(Node):
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('name',)

class ItemExpand(Node):
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('name',)

class ItemPair(Node):
    def __init__(self, label, value, coord=None):
        self.label = label
        self.value = value
        self.coord = coord

    def children(self):
        nodelist = []
        if self.value is not None: nodelist.append(("value", self.value))
        return tuple(nodelist)

    attr_names = ('label',)

class Send(Node):
    def __init__(self, msg, port, coord=None):
        self.msg = msg
        self.port = port
        self.coord = coord

    def children(self):
        nodelist = []
        if self.msg is not None: nodelist.append(("msg", self.msg))
        return tuple(nodelist)

    attr_names = ('port',)

class MsgSegmark(Node):
    def __init__(self, depth, coord=None):
        self.depth = depth
        self.coord = coord

    def children(self):
        nodelist = []
        if self.depth is not None: nodelist.append(("depth", self.depth))
        return tuple(nodelist)

    attr_names = ()

class MsgData(Node):
    def __init__(self, choice, data_exp, coord=None):
        self.choice = choice
        self.data_exp = data_exp
        self.coord = coord

    def children(self):
        nodelist = []
        if self.data_exp is not None: nodelist.append(("data_exp", self.data_exp))
        return tuple(nodelist)

    attr_names = ('choice',)

class MsgNil(Node):
    def __init__(self, coord=None):
        self.coord = coord

    def children(self):
        return ()

    attr_names = ()

class Goto(Node):
    def __init__(self, states, coord=None):
        self.states = states
        self.coord = coord

    def children(self):
        nodelist = []
        for i, child in enumerate(self.states or []):
            nodelist.append(("states[%d]" % i, child))
        return tuple(nodelist)

    attr_names = ()

class ID(Node):
    def __init__(self, name, coord=None):
        self.name = name
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('name',)

class NUMBER(Node):
    def __init__(self, value, coord=None):
        self.value = value
        self.coord = coord

    def children(self):
        nodelist = []
        return tuple(nodelist)

    attr_names = ('value',)

