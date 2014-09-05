#!/usr/bin/env python3

from queue import Empty as Empty
import pool

import network as net
import communication as comm
import components


def n_enqueued(nodes):
    '''
    Count the number of messages waiting for processing in inputs queues of the
    given nodes.
    It's temporary and expensive alternative to network schedule.
    '''
    n_msgs = 0

    for node_id in nodes:
        node = n.node(node_id)
        if node['type'] != 'vertex':
            continue
        vertex = node['obj']

        for q in vertex.inputs:
            n_msgs += q['queue'].size()

    return n_msgs


def printer(d):
    print(d)
    return ('send', {}, None)


if __name__ == '__main__':

    n = net.load(input_file='compiler/tests/a.out')

    # HACK: Add printer to the network
    pr = components.Printer('Printer', ['pin'], ['pout'], printer)
    pr_id = n.add_vertex(pr)

    root = n.node(n.root)['obj']

    n.network.add_edge(n.root, pr_id)
    root.outputs[0]['to'] = pr.inputs[0]['queue']

    root.outputs[0]['node_id'] = pr_id
    pr.inputs[0]['node_id'] = n.root - 1

    root.outputs[0] = pr.outputs[0]
    ########################################

    root.inputs[0]['queue'].put(comm.DataMessage(10))
    root.inputs[0]['queue'].put(comm.SegmentationMark(1))
    root.inputs[0]['queue'].put(comm.DataMessage(4))
    root.inputs[0]['queue'].put(comm.SegmentationMark(3))

    n.node(0)['obj'].start = True

    # Processing pool
    pm = pool.PoolManager(2)
    pm.start()

    vertices = {vertex_id for vertex_id in n.network.nodes()
                if n.node(vertex_id)['type'] == 'vertex'}

    schedule = vertices
    new_schedule = set()

    while True:

        for node_id in schedule:
            vertex = n.node(node_id, True)

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

            impact = vertex.collect_impact()
            print('Impact', impact)
            for vertex_id in impact[0] + impact[1]:

                if vertex_id is None:
                    vertex_id = vertex.id

                obj = n.node(vertex_id, True)

                if obj.is_ready():
                    new_schedule.add(vertex_id)

            if args is None:
                # 3.1 Input message were handled in fetch(), box execution
                #     is not required.
                continue

            # 4. Assemble all the data needed for the task to send in
            #    the processing pool.
            task_data = {'vertex_id': vertex.id, 'args': args}

            # 5. Send box function and task data to processing pool.
            #    NOTE: this call MUST always be non-blocking.
            pm.enqueue(vertex.core, task_data)
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
                response = pm.out_queue.get(need_block)

                if not n.has_node(response.vertex_id):
                    raise ValueError('Vertex corresponsing to the response '
                                     'does not exist.')

                vertex = n.node(response.vertex_id, True)

                # Commit the result of computation, e.g. send it to destination
                # vertices.
                sent_to = vertex.commit(response)
                vertex.busy = False

                impact = vertex.collect_impact()
                print('Impact', impact)
                for vertex_id in impact[0] + impact[1]:

                    if vertex_id is None:
                        vertex_id = vertex.id

                    obj = n.node(vertex_id, True)

                    if obj.is_ready():
                        new_schedule.add(vertex_id)


                print(new_schedule)
                schedule = new_schedule
                new_schedule = set()

            except Empty:
                break

    # Cleanup.
    pm.finish()
