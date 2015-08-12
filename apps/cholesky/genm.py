#!/usr/bin/env python3

import numpy as np
import sys

def gen_spd(m, n):

    dim = m * n
    print('Generating...')
    mrand = np.random.rand(dim, dim)

    print('Transforming...')
    msym = mrand + mrand.T

    msym += dim * np.eye(dim)

    #print('Testing...')
    #assert(all(np.linalg.eigvals(msym) > 1e-5))
    return msym

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('genm.py NBLOCKS SIZE')

    else:
        m, n = (int(v) for v in sys.argv[1:])
        A = gen_spd(m, n)
        A.dump('spd_%dx%d.dmp' % (m, n))
