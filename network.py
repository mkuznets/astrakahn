#!/usr/bin/env python3

import os
import sys

import components
import pool
import time
import communication as comm

from compiler.net import ast

from queue import Empty as Empty


class VerticesVisitor(components.NodeVisitor):

    def __init__(self):
        self.vertices = {}

    def generic_visit(self, node, children):
        if isinstance(node, components.Vertex):
            self.vertices.update({node.id: node})


class Network:

    def __init__(self, network, node_id=1000):

        self.network = network
        self.node_id = node_id

        # Cache of vertices in order to avoid network traversal.
        gv = VerticesVisitor()
        gv.traverse(self.network)
        self.vc = gv.vertices

        # Processing pool.
        self.pm = None

        self.initial_input = None

        self.ready = set()
        self.potential = set()

    def show(self):
        self.network.show()

    def init_pool(self, nproc):
        self.pm = pool.PoolManager(nproc)
        self.pm.start()

    def init_input(self, input_map):
        input_names = {port['name']: pid
                       for pid, port in enumerate(self.network.inputs)}

        for pname, container in input_map.items():
            if pname in input_names:
                pid = input_names[pname]

                for msg in container:
                    self.network.inputs[pid]['queue'].put(msg)

    def close_pool(self):
        self.pm.finish()

    def run(self, nproc=1):
        self.init_pool(nproc)

        self.ready = set(v for v in self.vc
                         if self.vc[v].is_ready() == (True, True))

        while True:
            vertex_id = self.ready.pop()
            vertex = self.vc[vertex_id]

            while True:
                assert(not vertex.busy)
                assert(vertex.is_ready() == (True, True))

                # 3. Get input message and form a list of arguments for the
                #    box function to apply.
                args = vertex.fetch()

                if args is None:
                    # 3.1 Input message were handled in fetch(), box execution
                    #     is not required.
                    self._impact(vertex)
                    break

                # 4. Assemble all the data needed for the task to send in
                #    the processing pool.
                task_data = {'vertex_id': vertex_id, 'args': args}

                # 5. Send box function and task data to processing pool.
                self.pm.enqueue(vertex.core, task_data)
                vertex.busy = True

                break

            # Check for responses from processing pool.
            while True:
                try:
                    response = self.pm.out_queue.get(not bool(self.ready))
                except Empty:
                    break

                if response.vertex_id not in self.vc:
                    raise ValueError('Vertex corresponsing to the response '
                                     'does not exist.')

                vertex = self.vc[response.vertex_id]

                # Commit the result of computation, e.g. send it to destination
                # vertices.
                sent_to = vertex.commit(response)
                vertex.busy = False

                self._impact(vertex)

            # Test potentially ready vertices.
            for vid in self.potential:
                vertex = self.vc[vid]
                if (vertex.is_ready() == (True, True)) and not vertex.busy:
                    self.ready.add(vid)
            self.potential.clear()

        self.close_pool()

    def _impact(self, vertex):
        if (vertex.is_ready() == (True, True)) and not vertex.busy:
            self.ready.add(vertex.id)

        self.potential |= set(dst[0] for dst in vertex.departures)
        del vertex.departures[:]
