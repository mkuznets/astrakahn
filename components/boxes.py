#!/usr/bin/env python3

import communication as comm
from . import abstract

class Transductor(abstract.Box):

    def __init__(self, name, inputs, outputs, core):
        super(Transductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):

        m = self.get(0)

        if m.is_segmark():
            # Special behaviour: sengmentation marks are sent through.
            self.send_to_all(m)
            return None

        else:
            return [m.content]

    def commit(self, response):

        if response.action == 'send':
            # Send output messages.
            self.send_out(response.out_mapping)
        else:
            print(response.action, 'is not implemented.')


class Printer(Transductor):
    '''
    Temporary class of vertex, just for debugging
    '''

    def fetch(self):
        m = self.get(0)
        return [m.content]

    def is_ready(self):

        # Check if there's an input message.
        input_ready = self.input_ready()
        return (input_ready, True)


class Inductor(abstract.Box):

    def __init__(self, name, inputs, outputs, core):
        super(Inductor, self).__init__(name, inputs, outputs)
        self.core = core

    def fetch(self):
        m = self.get(0)

        if m.is_segmark():
            # Special behaviour for segmentation marks.
            m.plus()
            self.send_to_all(m)
            return None

        else:
            return [m.content]

    def commit(self, response):

        if response.action == 'continue':

            cont = response.aux_data

            # Put the continuation back to the input queue
            self.put_back(0, cont)

            self.send_out(response.out_mapping)

        elif response.action == 'terminate':
            self.send_out(response.out_mapping)

        else:
            print(response.action, 'is not implemented.')


class DyadicReductor(abstract.Box):

    def __init__(self, name, inputs, outputs, core):
        super(DyadicReductor, self).__init__(name, inputs, outputs)
        self.core = core

    def is_ready(self):

        ## Test input availability.
        #

        # Reduction start: 2 messages from both channel are needed.
        input_ready = self.input_ready(any_channel=False)

        ## Test output availability.
        #

        output_ready = self.output_ready(range(1, self.n_outputs))
        # Test the 1st output separately since it must have enough space
        # for segmentation mark.
        output_ready &= self.output_ready((0,), space_needed=2)

        return (input_ready, output_ready)

    def fetch(self):

        # First reduction operand:
        term_a = self.get(0)

        if term_a.is_segmark():
            # Special behaviour for segmentation marks.
            term_a.plus()
            self.send_to_range(term_a, range(1, self.n_outputs))
            return None

        # Second reduction operand
        term_b = self.get(1)

        if term_b.is_segmark():
            # Special behaviour for segmentation marks.
            self.send_out({0: term_a})

            if term_b.n != 1:
                if term_b.n > 1:
                    term_b.minus()
                self.send_out({0: term_b})

            return None

        # Input messages are not segmarks: pass them to coordinator.
        return [term_a.content, term_b.content]

    def commit(self, response):

        if response.action == 'partial':
            # First output channel cannot be the destination of partial result.
            assert(0 not in response.out_mapping)
            self.send_out(response.out_mapping)

            # Put partial reduction result to the first input channel for
            # further reduction.
            self.put_back(0, response.aux_data)

        else:
            print(response.action, 'is not implemented.')


class Copier(abstract.Box):

    def __init__(self, name, inputs, outputs, core=None):
        super(Copier, self).__init__(name, inputs, outputs)

    def fetch(self):
        for i in range(self.n_inputs):
            try:
                m = self.get(i)
                self.send_to_all(m)

            except comm.Empty:
                continue
        return None
