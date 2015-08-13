#!/usr/bin/env python3

import os
import ctypes
import mmap
import struct
import numpy as np
import multiprocessing as mp
import posix_ipc as ipc
import random
import time
from functools import reduce

CTYPES_CONST = {
  'D': ctypes.c_double
}

def to_ctype(e):
    return CTYPES_CONST[e] if type(e) is str else e

class Array:

    def __init__(self, name, ctype, key=None):
        self.name = name
        self.ctype = ctype
        self.mm = None
        self.key = key

    def __getitem__(self, key):
        self.key = key

    def open(self):

        ctype_obj = reduce(lambda x, y: x * y,
                           [to_ctype(e) for e in self.ctype])

        size = ctypes.sizeof(ctype_obj)

        shm = ipc.SharedMemory(self.name, flags=ipc.O_CREAT, size=size)
        self.mm = mmap.mmap(shm.fd, size)
        shm.close_fd()

        arr = ctype_obj.from_buffer(self.mm, 0)
        nparr = np.ctypeslib.as_array(arr)

        return nparr[self.key] if self.key else nparr

    def remove(self):
        ctype_obj = reduce(lambda x, y: x * y,
                           [to_ctype(e) for e in self.ctype])

        size = ctypes.sizeof(ctype_obj)

        shm = ipc.SharedMemory(self.name, flags=ipc.O_CREAT, size=size)
        shm.unlink()

    def close(self):

        if not self.mm:
            return

        try:
            self.mm.close()
            self.mm = None

        except BufferError:
            pass

    def copy(self):
        return Array(self.name, self.ctype, self.key)
