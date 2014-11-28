#!/usr/bin/env python3

import sys
sys.path[0:0] = ['..', '../..']


import unittest
import net
from net import ast


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
        self.vertices.append((node.name, node.category, node.inputs,
                              node.outputs))


class ASTMorphism(ast.NodeVisitor):

    def visit_Net(self, node, children):
        return children['decls']

    def visit_Morphism(self, node, children):
        return ('morphism', node.trigger, children['morph_list'],
                children['override_list'])

    def visit_Morph(self, node, children):
        return ('morph', children['split'], children['map_list'],
                children['join'])

    def visit_MorphSplitMap(self, node, children):
        return ('morph_splitmap', children['split_map_list'], children['join'])

    def visit_MorphMapJoin(self, node, children):
        return ('morph_mapjoin', children['split'], children['map_join_list'])

    def visit_SplitMap(self, node, children):
        return ('splitmap', children['split'], children['map'])

    def visit_MapJoin(self, node, children):
        return ('mapjoin', children['map'], children['join'])

    def visit_Override(self, node, children):
        return ('override', children['join'], children['split'],
                children['sync'])

    def visit_ID(self, node, _):
        return node.value


class TestParser(unittest.TestCase):

    def _check_wiring(self, wiring, reference):
        ast = net.parse('net bar (a | b) connect {} end'.format(wiring))

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
        ast = net.parse('net bar (a | b) connect {} end'.format(vertex))

        visit = ASTVertex()
        visit.traverse(ast)

        self.assertEqual(len(visit.vertices), len(reference))

        for i, v in enumerate(visit.vertices):
            self.assertEqual(v, reference[i])

    def test_vertices(self):
        testcases = [

            # Simple vertex name.
            ('a', [('a', None, {}, {})]),

            # Vertex name with category
            ('TRANS:a', [('a', 'TRANS', {}, {})]),

            # Renaming brackets: list style.
            ('<a, b | box | m, c, ddd>', [
                ('box', None, {0: 'a', 1: 'b'}, {0: 'm', 1: 'c', 2: 'ddd'})
            ]),

            # Renaming brackets: dict- and list-style, category.
            ('<true=false, _1=aaa, a2=a5 | t:box | m, c, ddd>', [
                ('box', 't',
                 {'true': 'false', '_1': 'aaa', 'a2': 'a5'},
                 {0: 'm', 1: 'c', 2: 'ddd'})
            ]),

            # Renaming brackets: empty sections.
            ('<| box |>', [('box', None, {}, {})]),
        ]

        for vertex, ref in testcases:
            self._check_vertex(vertex, ref)

    #--------------------------------------------------------------------------

    def _check_morphism(self, testcase, reference):
        code = '''
        net foo (a|a)
          {}
        connect a end
        '''.format(testcase)

        ast = net.parse(code)
        visit = ASTMorphism()
        decls = visit.traverse(ast)

        self.assertEqual(len(decls), len(reference))

        for i, d in enumerate(decls):
            self.assertEqual(d, reference[i])


    def test_morphisms(self):

        #---------------------------------------------------------------------
        # Simple morphism

        testcase = '''
        morph (size) {div / b1 / joiner}
        '''

        reference = [
            ('morphism', 'size', [('morph', 'div', ['b1'], 'joiner')], [])
        ]

        self._check_morphism(testcase, reference)

        #---------------------------------------------------------------------
        # All 3 types of morphism declaration

        testcase = '''
        morph (nn) {
          div / b1, b2 / joiner,
          (aa / bb, cc / dd) / ee,
          zz / (yy / xx, ww / vv)
        }
        '''

        reference = [
            ('morphism', 'nn', [
                ('morph', 'div', ['b1', 'b2'], 'joiner'),
                ('morph_splitmap', [('splitmap', 'aa', 'bb'),
                                   ('splitmap', 'cc', 'dd')], 'ee'),
                ('morph_mapjoin', 'zz', [('mapjoin', 'yy', 'xx'),
                                          ('mapjoin', 'ww', 'vv')]),
            ], [])
        ]

        self._check_morphism(testcase, reference)

        #---------------------------------------------------------------------
        # Overrides

        testcase = '''
        morph (nn) {
          (aa / bb, cc / dd) / ee

          where joiner .. div = glue,
                ee .. aa = bypass
        }
        '''

        reference = [
            ('morphism', 'nn', [
                ('morph_splitmap', [('splitmap', 'aa', 'bb'),
                                   ('splitmap', 'cc', 'dd')], 'ee'),
            ], [
                ('override', 'joiner', 'div', 'glue'),
                ('override', 'ee', 'aa', 'bypass'),
            ])
        ]

        self._check_morphism(testcase, reference)

        #---------------------------------------------------------------------


if __name__ == '__main__':
    unittest.main()
