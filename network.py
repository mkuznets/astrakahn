#!/usr/bin/env python3

import os
import sys

import pool
import time
import visitors
import communication as comm
import collections

Result = collections.namedtuple('Result',
                                'vertex_id action dispatch aux_data tm')

from queue import Empty as Empty


class Network:

    def __init__(self, network, nproc=1):

        self.network = network

        # Cache of vertices in order to avoid network traversal.
        gv = visitors.NetworkVisitor()
        gv.traverse(self.network)
        self.vc = gv.vertices

        # Placeholder for pool object
        self.pm = pool.PoolManager(nproc)
        self.pm.start()

        self.ready = set()
        self.potential = set()

        self.profile = {}
        self.n_events = {}

    def show(self):
        self.network.show()

    def get_by_path(self, path):

        if path in self.vc:
            return self.vc[path]

        else:
            node = self.network.get_node_by_path(path)
            self.vc[path] = node

            pn = self.network.get_parent_net(path)
            pn.update_channels(path[-1])

            return node

    def init_input(self, input_map):
        input_names = {p.name: pid for pid, p in self.network.inputs.items()}

        for pname, container in input_map.items():
            if pname in input_names:
                pid = input_names[pname]

                for msg in container:
                    self.network.put(pid, msg)

    def run(self):

        self.ready = set(vid for vid, vertex in self.vc.items()
                         if vertex.is_ready() == (True, True))

        if not self.ready:
            print('No ready components.')
            return -1

        print('Start:', time.time())

        while True:

            vertex_id = self.ready.pop()
            vertex = self.get_by_path(vertex_id)

            assert(not vertex.busy)
            assert(vertex.is_ready() == (True, True))

            pn = self.network.get_parent_net(vertex_id)
            pn.update_channels(vertex_id[-1])

            #------------------------------------------------------------------

            # 3. Get input messages.
            msgs = vertex.fetch()
            task = vertex.run(msgs)

            response = None

            if task:

                if vertex.run_ext:
                    self.pm.enqueue(*task)
                    vertex.busy = True

                    self.potential.add(vertex.path)

                else:
                    core, p = task
                    output = core(*p['args'])

                    if output is None:
                        response = Result(vertex_id, '', {}, None, None)

                    else:
                        action, dispatch, aux_data = output

                        dispatch = {p: [comm.Record(msg) for msg in stream]
                                    for p, stream in dispatch.items()}

                        response = Result(vertex_id, action, dispatch, aux_data, None)

            else:
                self._impact(vertex)

            #------------------------------------------------------------------
            # TODO: fix repetition.
            # Test potentially ready vertices.
            for vid in self.potential:
                vertex = self.get_by_path(vid)
                if (vertex.is_ready() == (True, True)) and not vertex.busy:
                    self.ready.add(vid)
            self.potential.clear()
            #------------------------------------------------------------------

            while True:

                try:
                    if response:
                        prof = None

                    # Check for responses from processing pool.
                    elif not bool(self.ready):
                        response, prof = self.pm.out_qc.recv()

                    elif self.pm.out_qc.poll():
                        response, prof = self.pm.out_qc.recv()

                    else:
                        break

                except KeyboardInterrupt as e:
                    pinfo = {v: p/self.n_events[v] for v, p in self.profile.items()}
                    #import pickle
                    #pickle.dump(pinfo, open('pinfo', 'wb'))
                    print(pinfo)
                    return

                # Record profiling info
                if prof:
                    vid = response.vertex_id
                    self.profile[vid] = self.profile.get(vid, 0) + prof[0]
                    self.n_events[vid] = self.n_events.get(vid, 0) + 1
                #---------------------

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

                response = None

        self.pm.finish()

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
