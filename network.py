#!/usr/bin/env python3

import os
import sys

import pool
import time
import visitors

from queue import Empty as Empty


class Network:

    def __init__(self, network, node_id=1000):

        self.network = network
        self.node_id = node_id

        # Cache of vertices in order to avoid network traversal.
        gv = visitors.ExecutableVisitor()
        gv.traverse(self.network)
        self.vc = gv.vertices

        # Processing pool.
        self.pm = None

        self.initial_input = None

        self.ready = set()
        self.potential = set()

    def add_node(self, node):

        upd = visitors.ExecutableVisitor()
        upd.traverse(node)

        self.vc.update(upd.vertices)

    def set_id(self):
        t = self.node_id
        self.node_id += 1
        return t

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

        if not self.ready:
            print('No ready components.')
            return -1

        while True:
            vertex_id = self.ready.pop()
            vertex = self.vc[vertex_id]

            while True:

                assert(not vertex.busy)
                assert(vertex.is_ready() == (True, True))

                # 3. Get input message and form a list of arguments for the
                #    box function to apply.
                args = vertex.fetch()

                #if hasattr(vertex, 'state'):
                #    print(vertex.id, vertex.name, '--', vertex.state.name)

                if args is None:
                    # 3.1 Input message were handled in fetch(), box execution
                    #     is not required.
                    self._impact(vertex)

                    break

                #--------------------------------------------------------------

                if type(args) == dict:

                    # New stage.
                    if 1 in args:

                        import compiler.net.backend as compiler

                        stage = vertex.current_stage()

                        # Compile next stage.
                        nb = compiler.NetBuilder(stage.cores, stage.path, self.node_id)
                        obj = nb.compile_net(stage.ast)

                        self.node_id = nb.node_id

                        vertex.stages.append(obj)
                        vertex.wire_stages()

                        self.add_node(obj)
                        vertex.nodes[obj.id] = obj

                        for msg in args[1]:
                            target_id = obj.inputs[0]['vid']
                            self.vc[target_id].inputs[0]['queue'].put(msg)

                        self.potential.add(obj.inputs[0]['vid'])

                        #self.network.show()
                        #print()

                    if 2 in args:
                        for msg in args[2]:
                            vertex.merger.inputs[0]['queue'].put(msg)
                        self.potential.add(vertex.merger.id)

                    if 3 in args:

                        stage = None
                        stage_id = None

                        for i, s in enumerate(vertex.stages):
                            sv = visitors.SyncVisitor()
                            sv.traverse(s)

                            if sv.rfp is True:
                                stage = s
                                stage_id = i
                                break

                        if stage:
                            src = stage.inputs[0]['src']
                            dst = stage.outputs[0]['dst']

                            src_vertex = self.vc[src[0]]
                            dst_vertex = self.vc[dst[0]]

                            # Transfer messages enqueued to the stage to be
                            # removed.
                            old_queue = stage.inputs[0]['queue']
                            while not old_queue.is_empty():
                                m = old_queue.get()
                                dst_vertex.inputs[0]['queue'].put(m)

                            # Rewire to the next stage.
                            src_vertex.add_wire(src[1], dst_vertex, dst[1])

                            idv = visitors.IDVisitor()
                            idv.traverse(stage)

                            for i in idv.ids:
                                if i in self.vc:
                                    del self.vc[i]

                            self.ready -= set(idv.ids)
                            self.potential -= set(idv.ids)

                            del vertex.nodes[stage.id]
                            vertex.stages.pop(stage_id)

                        #self.network.show()
                        #print()

                    break

                #--------------------------------------------------------------

                # 4. Assemble all the data needed for the task to send in
                #    the processing pool.
                task_data = {'vertex_id': vertex_id, 'args': args}

                # 5. Send box function and task data to processing pool.
                self.pm.enqueue(vertex.core, task_data)
                vertex.busy = True

                break

            #------------------------------------------------------------------
            # TODO: fix repetition.
            # Test potentially ready vertices.
            for vid in self.potential:
                vertex = self.vc[vid]
                if (vertex.is_ready() == (True, True)) and not vertex.busy:
                    self.ready.add(vid)
            self.potential.clear()
            #------------------------------------------------------------------

            # Check for responses from processing pool.
            while True:
                try:
                    response = self.pm.out_queue.get(not bool(self.ready))
                except Empty:
                    break

                if response.vertex_id not in self.vc:

                    self.network.show()
                    print()

                    raise ValueError('Vertex (%d) corresponsing to the response '
                                     'does not exist.' % response.vertex_id)

                vertex = self.vc[response.vertex_id]

                # Commit the result of computation, e.g. send it to destination
                # vertices.
                vertex.commit(response)
                vertex.busy = False

                self._impact(vertex)

                #--------------------------------------------------------------
                # Test potentially ready vertices.
                for vid in self.potential:
                    vertex = self.vc[vid]
                    if (vertex.is_ready() == (True, True)) and not vertex.busy:
                        self.ready.add(vid)
                self.potential.clear()
                #--------------------------------------------------------------

        self.close_pool()

    def _impact(self, vertex):
        if (vertex.is_ready() == (True, True)) and not vertex.busy:
            self.ready.add(vertex.id)

        self.potential |= set(dst[0] for dst in vertex.departures)
        del vertex.departures[:]
