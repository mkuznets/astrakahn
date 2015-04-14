#!/usr/bin/env python3

import sys
sys.path[0:0] = ['..', '../..']


import unittest
import compiler.net as net
from compiler.net import ast


class ASTNetWiring(ast.NodeVisitor):

    def __init__(self):
        self.exprs = []

    def visit_Net(self, node, children):
        self.exprs.append(children['wiring'])

    def visit_BinaryOp(self, node, children):
        return (node.op, children['left'], children['right'])

    def visit_UnaryOp(self, node, children):
        return (node.op, children['operand'])

    def visit_Vertex(self, node, children):
        return node.name


class ASTVertex(ast.NodeVisitor):

    def __init__(self):
        self.vertices = []

    def visit_Vertex(self, node, _):
        self.vertices.append((node.name, node.inputs, node.outputs))


class ASTMorphism(ast.NodeVisitor):

    def visit_Net(self, node, children):
        return children['decls']

    def visit_DeclList(self, node, children):
        return children['decls']

    def visit_Morphism(self, node, children):
        return ('morph', node.split, node.map, node.join)

    def visit_ID(self, node, _):
        return node.value


class TestParser(unittest.TestCase):

    def _check_wiring(self, wiring, reference):
        ast = net.parse('net bar (a | b) connect %s end' % wiring,
                        output_handler=False)

        visit = ASTNetWiring()
        visit.traverse(ast)

        self.assertEqual(len(visit.exprs), 1)
        self.assertEqual(visit.exprs[0], reference)

    def test_wiring(self):

        testcases = [
            ('(a .. b || c *)\\', ('\\', ('||', ('..', 'a', 'b'), ('*', 'c')))),
            ('a .. b || c',       ('||', ('..', 'a', 'b'), 'c')),
            ('a .. (b || c)',     ('..', 'a', ('||', 'b', 'c'))),
            ('a .. b .. c',       ('..', ('..', 'a', 'b'), 'c')),
            ('a || b || c',       ('||', ('||', 'a', 'b'), 'c')),
            ('a || c .. b*',      ('||', 'a', ('..', 'c', ('*', 'b')))),
            ('a || c .. b\\',     ('||', 'a', ('..', 'c', ('\\', 'b')))),
            ('a || (c .. b)*\\',  ('||', 'a', ('\\', ('*', ('..', 'c', 'b'))))),
            ('a || (c .. b)\\*',  ('||', 'a', ('*', ('\\', ('..', 'c', 'b'))))),
        ]

        for wiring, ref in testcases:
            self._check_wiring(wiring, ref)

    #--------------------------------------------------------------------------

    def _check_vertex(self, vertex, reference):
        ast = net.parse('net bar (a | b) connect %s end' % vertex,
                        output_handler=False)

        visit = ASTVertex()
        visit.traverse(ast)

        self.assertEqual(len(visit.vertices), len(reference))

        for i, v in enumerate(visit.vertices):
            self.assertEqual(v, reference[i])

    def test_vertices(self):
        testcases = [

            # Simple vertex name.
            ('a', [('a', {}, {})]),

            # Renaming brackets: list style.
            ('<a, b | box | m, c, ddd>', [
                ('box', ['a', 'b'], ['m', 'c', 'ddd'])
            ]),

            # Renaming brackets: dict- and list-style, category.
            ('<true=false, _1=aaa, a2=a5 | box | m, c, ddd>', [
                ('box', {'true': 'false', '_1': 'aaa', 'a2': 'a5'},
                 ['m', 'c', 'ddd'])
            ]),

            # Renaming brackets: empty sections.
            ('<| box |>', [('box', {}, {})]),

            # Renaming brackets: single section.
            ('<a, b| box', [('box', ['a', 'b'], {})]),
            ('box|_1 = ololo>', [('box', {}, {'_1': 'ololo'})]),

            # Merger
            ('<a| ~ |b, c>', [('~', ['a'], ['b', 'c'])]),
        ]

        for vertex, ref in testcases:
            self._check_vertex(vertex, ref)

    #--------------------------------------------------------------------------

    def _check_morphism(self, testcase, reference):
        code = '''
        net foo (a|a)
          %s
        connect a end
        ''' % testcase

        ast = net.parse(code, output_handler=False)
        visit = ASTMorphism()
        decls = visit.traverse(ast)

        self.assertEqual(len(decls), len(reference))

        for i, d in enumerate(decls):
            self.assertEqual(d, reference[i])


    def test_morphisms(self):

        #---------------------------------------------------------------------
        # Simple morphism

        testcase = '''
        morph {div / b1 / joiner}
        '''

        reference = [
            ('morph', 'div', 'b1', 'joiner')
        ]

        self._check_morphism(testcase, reference)

        #---------------------------------------------------------------------
        # All 3 types of morphism declaration

        testcase = '''
        morph {
            div / b1, b2 / joiner,
            foo / b3 / bar
        }
        '''

        reference = [
            ('morph', 'div', 'b1', 'joiner'),
            ('morph', 'div', 'b2', 'joiner'),
            ('morph', 'foo', 'b3', 'bar')
        ]

        self._check_morphism(testcase, reference)

        #---------------------------------------------------------------------


if __name__ == '__main__':
    unittest.main()
