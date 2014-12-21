class RuntimeVisitor(object):

    def generic_visit(self, node, children):
        pass

    def traverse(self, node):

        children = {}

        if hasattr(node, 'nodes'):
            for id, c in node.nodes.items():
                outcome = self.traverse(c)
                children[id] = outcome

        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, children) if visitor else None


class ExecutableVisitor(RuntimeVisitor):

    def __init__(self):
        self.vertices = {}

    def generic_visit(self, node, children):
        import components

        if isinstance(node, components.Vertex) \
                or isinstance(node, components.StarNet):
            self.vertices.update({node.id: node})

class CoreVisitor(RuntimeVisitor):

    def __init__(self):
        self.cores = {}

    def generic_visit(self, node, children):
        import components

        if isinstance(node, components.Box)\
                and node.core\
                and node.core.__name__.startswith('c_'):
            self.cores[node.core.__name__[2:]] = ('core', node.core)

