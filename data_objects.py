#!/usr/bin/env python3

import numpy as np
import collections

objects = {}

ref = collections.namedtuple('ref', 'name')
obj = collections.namedtuple('obj', 'ref data')

def to_numpy(obj_ref):
    '''
    Converts object reference to 1D numpy array
    '''
    obj = objects[obj_ref.name]
    np_array = np.frombuffer(obj.get_obj())
    return np_array

def new(name, obj):
    objects[name] = obj
