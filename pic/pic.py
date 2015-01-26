#!/usr/bin/env python3

'''
net PIC (in | out)

  net fps_pic (_1| _1, __output__, __remove__)

    synch fps_begin [FPS_PORT=_1, STAGE_IN=_1] "../compiler/net/tests/star/fps_begin.sync"
    synch fps_end [FPS_PORT=_1, STAGE_OUT=_1] "../compiler/net/tests/star/fps_end.sync"

    net fps_solve_phi (_1| _1, __output__, __remove__)
      synch fps_begin [FPS_PORT=_1, STAGE_IN=in] "../compiler/net/tests/star/fps_begin.sync"
      synch fps_end [FPS_PORT=_1, STAGE_OUT=out] "../compiler/net/tests/star/fps_end.sync"
      synch rfp_test [FPS_PORT=_1] "../compiler/net/tests/star/rfp_test.sync"
    connect
      rfp_test .. fps_begin .. <in|solve_phi|out> .. fps_end
    end

    net scatter_reduce (_1 | _1)
    connect
      join_grid .. scatter_exchange .. assemble_grid
    end

    net field_reduce (_1 | _1)
    connect
      join_grid .. assemble_grid
    end

    connect
      fps_begin .. scatter .. (fps_solve_phi)* .. fps_end
    end

connect
  #<in|scatter|> .. (fps_solve_phi)* .. solve_e .. gather .. <|move|out>
  #<in|scatter|> .. solve_phi .. solve_e .. gather .. <|move|out>

  #<in|scatter|out> ||
  (<in|~|_1> ..
    split_grid .. (fps_pic)*
  .. <_1|~|out>)
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

    n0 = (m['NPF'] if 'NPF' in m else m['NP']) * m['dh'] / float(m['L'])

    rho /= n0
    rho -= 1

    if 'rghost' in m:
        m['rghost'][0] /= n0
        m['rghost'][0] - 1

    return ('send', {0: m}, None)


def c_scatter_exchange(m):
    '1T'

    n = len(m['grids'])

    for i, g, lghost, rghost in m['grids']:
        grid = m['grids'][(i+1) % n][1][:,0]
        grid[0] += rghost[0]

    return ('send', {0: m}, None)

#------------------------------------------------------------------------------


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

    if m['residual'] < 4e-3:
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


def c_split_grid(m):
    '1I'

    import numpy as np

    if 'nsplit' not in m:
        # Partition is not needed.
        return ('terminate', {0: m}, None)

    if 'nchunk' not in m:
        # Initialize induction.

        m['nchunk'] = 0

        # Sort particles by coordinate.
        m['part'] = m['part'][m['part'][:,0].argsort()]

        # Divide grid into nearly equal parts.
        m['grid'] = np.array_split(m['grid'], m['nsplit'])

        part_fragments = []

        s = 0
        for f in m['grid']:

            sc = s * m['dh']
            ec = (s + f.shape[0] - 1) * m['dh']

            l, r = np.searchsorted(m['part'][:,0], [sc, ec + m['dh']])
            part_fragments.append(m['part'][l:r])

            s += f.shape[0]

        m['part'] = part_fragments

        m['sc'] = 0

    nchunk = m['nchunk']

    chunk = m.copy()
    chunk['part'] = m['part'][nchunk]
    chunk['grid'] = m['grid'][nchunk]

    chunk['lghost'] = m['grid'][nchunk-1][-1].copy()
    chunk['rghost'] = m['grid'][(nchunk+1) % m['nsplit']][0].copy()

    chunk['NG'] = len(chunk['grid'])
    chunk['NP'] = len(chunk['part'])

    chunk['NGF'] = m['NG']
    chunk['NPF'] = m['NP']

    chunk['sc'] = m['sc']
    m['sc'] += chunk['NG']

    chunk['splitted'] = True

    m['nchunk'] += 1

    if m['nchunk'] < m['nsplit']:
        # Generate with continuation
        return ('continue', {0: chunk},  m)
    else:
        return ('terminate', {0: chunk},  None)


def c_join_grid(acc, term):
    '1MU'

    import numpy as np

    def _print(m):
        arrays = []
        primitive = []
        for label in m:
            if type(m[label]) is np.ndarray:
                arrays.append('%s [%d]' % (label, len(m[label])))
            elif type(m[label]) is list:
                primitive.append('%s [%d]' % (label, len(m[label])))
            else:
                primitive.append('%s = %s' % (label, str(m[label])))

        #print('|', ', '.join(arrays))
        #print('|', ', '.join(primitive))
        #print()


    #_print(term)
    _print(acc)

    if 'grids' not in acc:
        acc['grids'] = [(acc['nchunk'], acc['grid'], acc['lghost'], acc['rghost'])]
        acc['parts'] = [(acc['nchunk'], acc['part'])]

        acc['indexes'] = [(acc['sc'], acc['NG'])]

        del acc['part'], acc['grid'], acc['nchunk']
        acc.pop('lghost', None)
        acc.pop('rghost', None)


    acc['grids'].append((term['nchunk'], term['grid'], term['lghost'], term['rghost']))
    acc['parts'].append((term['nchunk'], term['part']))
    acc['indexes'].append((term['sc'], term['NG']))

    acc['grids'] = sorted(acc['grids'], key=lambda s: s[0])
    acc['parts'] = sorted(acc['parts'], key=lambda s: s[0])
    acc['indexes'] = sorted(acc['indexes'], key=lambda s: s[0])

    acc['NP'] += term['NP']

    assert(len(acc['grids']) == len(acc['parts']))
    assert(len(acc['grids']) <= acc['nsplit'])

    return ('partial', {}, acc)

def c_assemble_grid(m):
    '1T'

    import numpy as np
    import ctypes as ct

    # Test for the grids to form a contiguous region.
    for i in range(1, len(m['indexes'])):
        assert(m['indexes'][i][0] == sum(m['indexes'][i-1]))

    m['sc'] = m['indexes'][0][0]
    m['NG'] = sum(m['indexes'][-1])

    m['part'] = np.concatenate(tuple(p[1] for p in m['parts']))
    m['grid'] = np.concatenate(tuple(p[1] for p in m['grids']))

    del m['grids'], m['parts'], m['indexes']

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
        'L': L, 'dt': dt, 'dh': dh, 'n0': n0, 'NT': NT, 'sc': 0, 't': 0,
        'nsplit': 3
    }

    return problem

m = init()

__input__ = {'in': [
    comm.Record(m),
    comm.SegmentationMark(0)
]}

def __output__(stream):
    '1H'

    def _print(m):
        arrays = []
        primitive = []
        for label in m:
            if type(m[label]) is np.ndarray:
                arrays.append('%s [%d]' % (label, len(m[label])))
            else:
                primitive.append('%s = %s' % (label, str(m[label])))

        print('|', ', '.join(arrays))
        print('|', ', '.join(primitive))
        print()

    import numpy as np

    for i, ch, msg in stream:
        if msg.is_segmark():
            print(msg, "\n")
        else:
            c = msg.content
            #print('splitted' in c,
            #      c['grid'][:,0])
            _print(msg.content)

            #w = open('1' if 'splitted' in c else '2', 'w')
            #w.write("\n".join(str(i) for i in c['grid'][:,0]))
            #w.close()

import astrakahn
astrakahn.start()
