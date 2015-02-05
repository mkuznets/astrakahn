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


class ExecutableVisitor:

    def __init__(self):
        self.vertex_path = []
        self.vertices = {}

    def generic_visit(self, node, children):
        if node.executable:
            self.vertices.update({tuple(self.vertex_path): node})
            node.path = tuple(self.vertex_path)

    def traverse(self, node):

        children = {}

        if node.id > 0:
            self.vertex_path.append(node.id)

        if hasattr(node, 'nodes'):
            for id, c in node.nodes.items():
                outcome = self.traverse(c)
                children[id] = outcome

        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)

        result = visitor(node, children) if visitor else None

        if node.id > 0:
            self.vertex_path.pop()
        return result


class CoreVisitor(RuntimeVisitor):

    def __init__(self):
        self.cores = {}

    def generic_visit(self, node, children):
        import components

        if isinstance(node, components.Box)\
                and node.core\
                and node.core.__name__.startswith('c_'):
            self.cores[node.core.__name__[2:]] = ('core', node.core)


class SyncVisitor(RuntimeVisitor):

    def __init__(self):
        self.rfp = None

    def generic_visit(self, node, children):
        import components

        if isinstance(node, components.Sync):
            if self.rfp is None:
                self.rfp = True

                if (node.name == 'fps_begin' or node.name == 'fps_end')\
                        and node.state_name != 'bypass':
                    self.rfp = False

class IDVisitor(RuntimeVisitor):

    def __init__(self):
        self.ids = []

    def generic_visit(self, node, children):
        import components
        self.ids.append(node.id)
