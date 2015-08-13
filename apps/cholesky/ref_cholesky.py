#!/usr/bin/env python3

import numpy as np

m, n = 16, 128

A = np.load('spd_%dx%d.dmp' % (m, n))
AA = A.copy()

AB = [np.hsplit(B, m) for B in np.vsplit(A, m)]

for k in range(m):
    AB[k][k] = np.linalg.cholesky(AB[k][k])

    for i in range(k+1, m):
        AB[i][k] = np.dot(AB[i][k], np.linalg.inv(AB[k][k].T))

    for i in range(k+1, m):
        for j in range(k+1, i+1):
            AB[i][j] -= np.dot(AB[i][k], AB[j][k].T)

for i in range(1, m):
    for j in range(0, i):
        AB[j][i].fill(0.0)

LL = np.hstack([np.vstack([AB[i][j] for i in range(m)]) for j in range(m)])


L = np.linalg.cholesky(AA)

print(np.all(np.isclose(LL, L).astype(int)))
