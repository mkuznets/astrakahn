#!/usr/bin/env python3

import os
import sys

import pool
import time
import visitors

from queue import Empty as Empty


class Network:

    def __init__(self, network):

        self.network = network

        # Cache of vertices in order to avoid network traversal.
        gv = visitors.NetworkVisitor()
        gv.traverse(self.network)
        self.vc = gv.vertices

        self.network.make_root()
        self.network.update_channels(0)

        # Put references of channels into the vertices.
        for path, vertex in gv.nets.items():
            if path:
                pn = self.get_parent_net(path)
                pn.init_ext_streams(path[-1])

        for path, vertex in gv.vertices.items():
            pn = self.get_parent_net(path)
            pn.update_channels(path[-1])

        # Placeholder for pool object
        self.pm = None

        self.ready = set()
        self.potential = set()

    def show(self):
        self.network.show()

    def get_parent_net(self, path):
        return self.network.get_node_by_path(path[:-1])

    def get_by_path(self, path):
        if path in self.vc:
            return self.vc[path]
        else:
            node = self.network.get_node_by_path(path)
            self.vc[path] = node

            pn = self.get_parent_net(path)
            pn.update_channels(path[-1])

            return node

    def init_input(self, input_map):
        input_names = {p.name: i for i, p in self.network.inputs.items()}

        for pname, container in input_map.items():
            if pname in input_names:
                pid = input_names[pname]

                for msg in container:
                    self.network.put(pid, msg)

    def init_pool(self, nproc):
        self.pm = pool.PoolManager(nproc)
        self.pm.start()

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
            vertex = self.get_by_path(vertex_id)

            pn = self.get_parent_net(vertex_id)
            pn.update_channels(vertex_id[-1])

            while True:

                assert(not vertex.busy)
                assert(vertex.is_ready() == (True, True))

                # 3. Get input messages.
                msgs = vertex.fetch()

                #--------------------------------------------------------------

                #if type(args) == dict:

                #    # New stage.
                #    if 1 in args:

                #        import compiler.net.backend as compiler

                #        stage = vertex.current_stage()

                #        # Compile next stage.
                #        nb = compiler.NetBuilder(stage.cores, stage.path, self.node_id)
                #        obj = nb.compile_net(stage.ast)

                #        self.node_id = nb.node_id

                #        vertex.stages.append(obj)
                #        vertex.wire_stages()

                #        self.add_node(obj)
                #        vertex.nodes[obj.id] = obj

                #        for msg in args[1]:
                #            target_id = obj.inputs[0]['vid']
                #            self.vc[target_id].inputs[0]['queue'].put(msg)

                #        self.potential.add(obj.inputs[0]['vid'])

                #    if 2 in args:
                #        for msg in args[2]:
                #            vertex.merger.inputs[0]['queue'].put(msg)
                #        self.potential.add(vertex.merger.id)

                #    if 3 in args:

                #        stage = None
                #        stage_id = None

                #        for i, s in enumerate(vertex.stages):
                #            sv = visitors.SyncVisitor()
                #            sv.traverse(s)

                #            if sv.rfp is True:
                #                stage = s
                #                stage_id = i
                #                break

                #        if stage:
                #            src = stage.inputs[0]['src']
                #            dst = stage.outputs[0]['dst']

                #            src_vertex = self.vc[src[0]]
                #            dst_vertex = self.vc[dst[0]]

                #            # Transfer messages enqueued to the stage to be
                #            # removed.
                #            old_queue = stage.inputs[0]['queue']
                #            while not old_queue.is_empty():
                #                m = old_queue.get()
                #                dst_vertex.inputs[0]['queue'].put(m)

                #            # Rewire to the next stage.
                #            src_vertex.add_wire(src[1], dst_vertex, dst[1])

                #            idv = visitors.IDVisitor()
                #            idv.traverse(stage)

                #            for i in idv.ids:
                #                if i in self.vc:
                #                    del self.vc[i]

                #            self.ready -= set(idv.ids)
                #            self.potential -= set(idv.ids)

                #            del vertex.nodes[stage.id]
                #            vertex.stages.pop(stage_id)

                #        #self.network.show()
                #        #print()

                #    break

                #--------------------------------------------------------------

                task = vertex.run(msgs)

                if task is None:
                    self._impact(vertex)
                    break

                self.pm.enqueue(*task)
                vertex.busy = True
                break

            #------------------------------------------------------------------
            # TODO: fix repetition.
            # Test potentially ready vertices.
            for vid in self.potential:
                vertex = self.get_by_path(vid)
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

                vertex = self.get_by_path(response.vertex_id)

                # Commit the result of computation, e.g. send it to destination
                # vertices.
                vertex.commit(response)
                vertex.busy = False

                self._impact(vertex)

                #--------------------------------------------------------------
                # Test potentially ready vertices.
                for vid in self.potential:
                    vertex = self.get_by_path(vid)
                    if (vertex.is_ready() == (True, True)) and not vertex.busy:
                        self.ready.add(vid)
                self.potential.clear()
                #--------------------------------------------------------------

        self.close_pool()

    def _impact(self, vertex):
        if (vertex.is_ready() == (True, True)) and not vertex.busy:
            self.ready.add(vertex.path)

        for dst_port in vertex.departures:

            dst_id = -1e6
            v = vertex
            path = vertex.path[:-1]
            parent_net = self.network.get_node_by_path(path)

            # Search the destination node "bottom-up": when a node send a
            # message out of its net, we need to bypass "virtual" streams to
            # get a "real" node.
            while True:
                stream = parent_net.streams[v.outputs[dst_port].sid]
                dst_id, dst_port = stream.dst

                if dst_id < 0:
                    if not path:
                        raise RuntimeError('Destination vertex not found.')

                    parent_id = parent_net.id
                    path = path[:-1]
                    parent_net = self.network.get_node_by_path(path)
                    v = parent_net.get_node(parent_id)
                else:
                    break

            # Found node is not necesserily executable, in which case we need
            # to go into it and find an executable node.
            while True:
                dst_node = parent_net.get_node(dst_id)

                if dst_node.executable:
                    break
                else:
                    path += (dst_id,)
                    sid = dst_node._get_ext_stream_input(dst_port)
                    stream = dst_node.streams[sid]
                    dst_id, dst_port = stream.dst
                    parent_net = dst_node

            self.potential.add(path + (dst_id,))

            #--------------

        # TODO: fix the ugly hack for nets.
        if hasattr(vertex, 'fire_nodes'):
            self.potential.update(vertex.fire_nodes)
            vertex.fire_nodes.clear()


        vertex.departures.clear()
