#!/usr/bin/env python3

'''
net PIC (in | out)


  net fps_solve_phi (_1| _1, __output__)
    synch fps_begin [FPS_PORT=_1, STAGE_IN=in] "../compiler/net/tests/star/fps_begin.sync"
    synch fps_end [FPS_PORT=_1, STAGE_OUT=out] "../compiler/net/tests/star/fps_end.sync"
  connect
    fps_begin.. <in|solve_phi|out> .. fps_end
  end

connect
  <in|scatter|> .. (fps_solve_phi)* .. solve_e .. gather .. <|move|out>
end
'''


import communication as comm

#------------------------------------------------------------------------------

def c_scatter(m):
    '1T'

    rho = m['grid'][:,0]

    # Calculate charge densities.
    for x, vx, _ in m['part']:
        xd = x / m['dh']
        x_int, x_shift = int(xd), xd - int(xd)

        li, ri = x_int, x_int+1

        assert(m['sc'] <= li < (m['sc'] + m['NG']))
        assert(ri >= m['sc'])

        rho[li - m['sc']] += (1 - x_shift)

        if ri < (m['sc'] + m['NG']):
            rho[ri - m['sc']] += x_shift
        else:
            if 'rghost' in m:
                m['rghost'][0] += x_shift
            else:
                rho[0] += x_shift

    n0 = m['NP'] * m['dh'] / float(m['L'])
    rho /= n0
    rho -= 1

    return ('send', {0: m}, None)


def c_solve_phi(m):
    '1T'

    import numpy as np

    rho = m['grid'][:,0]
    phi = m['grid'][:,1]
    phi_p = m['grid'][:,2]

    dh2 = m['dh'] ** 2

    # Copy old phi values
    phi_p[:] = phi[:]

    # Leftmost phi
    lghost = m['lghost'][1] if 'lghost' in m else phi_p[-1]
    phi[0] = .5 * (lghost + phi_p[1] + rho[0] * dh2)

    for i in range(1, m['NG']-1):
        phi[i] = .5 * (phi_p[i-1] + phi_p[i+1] + rho[i] * dh2)

    # Rightmost phi
    rghost = m['rghost'][1] if 'rghost' in m else phi_p[0]
    phi[-1] = .5 * (phi_p[-2] + rghost + rho[-1] * dh2)

    m['residual'] = np.linalg.norm(phi - phi_p, ord=np.inf)

    if m['residual'] < 1e-3:
        m['ffp'] = True

    return ('send', {0: m}, None)


def c_solve_e(m):
    '1T'

    import numpy as np

    phi = m['grid'][:,1]
    E = m['grid'][:,3]

    lghost = m['lghost'][1] if 'lghost' in m else phi[-1]
    E[0] = .5 * (lghost - phi[1])

    for i in range(1, m['NG']-1):
        E[i] = .5 * (phi[i-1] - phi[i+1])

    rghost = m['rghost'][1] if 'rghost' in m else phi[0]
    E[-1] = .5 * (phi[-2] - rghost)

    E /= m['dh']

    return ('send', {0: m}, None)


def c_gather(m):
    '1T'

    import numpy as np

    E = m['grid'][:,3]
    Xp = m['part'][:,0]
    Ep = m['part'][:,2]

    for i in range(m['NP']):
        x, xd = Xp[i], int(Xp[i] / m['dh'])
        x_shift = x / m['dh'] - xd
        Ep[i] = E[xd % m['NG']] * (1 - x_shift) + E[(xd + 1) % m['NG']] * x_shift

    return ('send', {0: m}, None)


def c_move(m):
    '1T'

    import numpy as np

    dt = m['dt']

    xs = m['sc'] * m['dh']
    xe = xs +  m['NG'] * m['dh']

    #print(xs, xe)

    left = []
    right = []
    p = 0

    if m['t'] == 0:

        for i in range(m['NP']):
            x, v, E = m['part'][i]

            v -= E * dt/2
            v += E * dt

            x += v * dt

            if x < xs:
                left.append((x, v, E))
            elif x >= xe:
                right.append((x, v, E))
            else:
                m['part'][p] = (x, v, E)
                p += 1

    else:

        for i in range(m['NP']):
            x, v, E = m['part'][i]

            v += E * dt
            x += v * dt

            if x < xs:
                left.append((x, v, E))
            elif x >= xe:
                right.append((x, v, E))
            else:
                m['part'][p] = (x, v, E)
                p += 1

    m['part'][p:] = (0, 0, 0)

    m['t'] += 1
    m['left'] = np.array(left)
    m['right'] = np.array(right)

    return ('send', {0: m}, None)

#------------------------------------------------------------------------------


def init(L=100, NG=1025, NP=10000, vb=3, dt=0.1, NT=300):
    from random import random
    import numpy as np
    import math

    vmin = - 5. * vb
    vmax = + 5. * vb
    vdiff = vmax - vmin

    f = lambda v, vb : .5 * (math.exp(-(v - vb)**2 / 2.) +
                             math.exp(-(v + vb)**2 / 2.))
    fmax = f(vb, vb)

    def distribution():
        v = vmin + vdiff * random()
        x = fmax * random()

        fv = f(v, vb)

        if x > fv:
            return distribution()
        else:
            return v

    grid = np.zeros((NG, 4))  # Grid array (rho | phi | phi_p | E)
    part = np.zeros((NP, 3))  # Particles (x | v | E)

    for i in range(NP):
        part[i] = (L * random(), distribution(), 0)

    dh = float(L) / (NG)    # grid step
    n0 = (float(NP) / L) * dh

    problem = {
        'grid': grid, 'NG': NG, 'part': part, 'NP': NP,
        'L': L, 'dt': dt, 'dh': dh, 'n0': n0, 'NT': NT, 'sc': 0, 't': 0, 'rfp': True
    }

    return problem

m = init()
m = comm.Record(m)

__input__ = {'in': [m]}

def __output__(stream):
    '1H'
    for i, ch, msg in stream:
        print(msg)

import astrakahn
astrakahn.start()
