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
        self.vertices_cache = gv.vertices

        # Processing pool.
        self.pm = None

        self.initial_input = None

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

    def run(self, nproc=2):
        self.init_pool(nproc)

        while True:
            for id, vertex in self.vertices_cache.items():

                # NOTE: schedule (ready_boxes list) is now responsible for
                # availablility of boxes.
                # 1. Test if the box is already running. If it is, skip it.
                if vertex.busy:
                    continue

                # 2. Test if the conditions on channels are sufficient for the
                #    box execution. Is they're not, skip the box.
                if vertex.is_ready() != (True, True):
                    continue

                # 3. Get input message and form a list of arguments for the
                #    box function to apply.
                args = vertex.fetch()

                if args is None:
                    # 3.1 Input message were handled in fetch(), box execution
                    #     is not required.
                    continue

                # 4. Assemble all the data needed for the task to send in
                #    the processing pool.
                task_data = {'vertex_id': id, 'args': args}

                # 5. Send box function and task data to processing pool.
                #    NOTE: this call MUST always be non-blocking.
                self.pm.enqueue(vertex.core, task_data)
                vertex.busy = True

            # Check for responses from processing pool.

            while True:
                try:
                    # Wait responses from the pool if there're no other messages in
                    # queues to process.
                    need_block = False

                    if need_block:
                        print("NOTE: waiting result")

                    # Vertex response.
                    response = self.pm.out_queue.get(need_block)

                    if response.vertex_id not in self.vertices_cache:
                        raise ValueError('Vertex corresponsing to the response '
                                         'does not exist.')

                    vertex = self.vertices_cache[response.vertex_id]

                    # Commit the result of computation, e.g. send it to destination
                    # vertices.
                    sent_to = vertex.commit(response)
                    vertex.busy = False

                except Empty:
                    break

        self.close_pool()
