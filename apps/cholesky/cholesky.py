#!/usr/bin/env python3

'''
net Cholesky (in | result)
  synch Router
  synch join
  synch cnt
  synch segm
  synch MergeSwitch
  synch ResultFilter
  tab [i, j] synch join2
connect
  <in|splitter|iblocks>

  .. (<iblocks, cblocks|MergeSwitch|blocks>
       .. <blocks|Router|akk,aik,aij>
       .. <akk|InitFact|_1,result> .. dupl|lkk> .. <lkk,aik|join
       .. TrigSolve|_1,result> .. dupl2|lik> .. <aij,lik|cnt|aij,lik,sg> .. join2 .. <aij,sg|segm
       .. SymRank|cblocks>
     ) \\ .. <result|ResultFilter .. ResultCombiner|result>
end
'''


import communication as comm

#------------------------------------------------------------------------------

def c_splitter(m):
    '1I'
    import numpy as np
    from collections import deque

    if 'blocks' not in m:
        MB = [np.hsplit(B, m['Nb']) for B in np.vsplit(m['A'], m['Nb'])]

        blocks = deque()

        for i in range(m['Nb']):
            for j in range(i+1):
                blocks.append({'Nb': m['Nb'], 'i': i, 'j': j,
                               'Aij': MB[i][j]})

        m['blocks'] = blocks

    msg = m['blocks'].popleft()

    print('Coord', msg['i'], msg['j'])

    return ('continue' if m['blocks'] else 'terminate',
            {0: [msg]},
            m if m['blocks'] else None)


s_Router = '''
@Nb
synch Router (_1 | _1, _2, _3)
{
  state int(32) k = 0;

  start {
    on:
      _1.(Aij, i, j) & [i==j && i==k] {
        send this => _1;
      }

      _1.(Aij, j) & [j == k] { send this => _2; }

    elseon:
      _1.(Aij) { send this => _3; }
      _1.@d    {
        set k = [k + 1];
        send this => _1, this => _2, this => _3;
      }
  }
}
'''


def c_InitFact(m):
    '2T'
    import numpy as np
    m['Lij'] = np.linalg.cholesky(m['Aij'])
    m['Nr'] = m['Nb'] - m['i'] - 1
    del m['Aij']
    r = {'Lij': m['Lij'], 'Nb': m['Nb'], 'i': m['i'], 'j': m['j']}
    return ('send', {0: [m], 1: [r]}, None)


def c_TrigSolve(m):
    '2T'
    import numpy as np
    m['Lij'] = np.dot(m['Aij'], np.linalg.inv(m['Lij'].T))
    m['Nr'] = m['Nb']
    del m['Aij']
    r = {'Lij': m['Lij'], 'Nb': m['Nb'], 'i': m['i'], 'j': m['j']}
    return ('send', {0: [m], 1: [r]}, None)


def c_SymRank(m):
    '1T'
    import numpy as np
    m['Aij'] -= np.dot(m['Lik'], m['Ljk'].T)
    del m['Lik'], m['Ljk']
    return ('send', {0: [m]}, None)


def c_dupl(m):
    '1I'
    if m['Nr'] <= 0:
        return ('terminate', {}, None)

    m['Nr'] -= 1
    msg = m.copy()
    del msg['Nr']

    return ('continue', {0: [msg]}, m)


def c_dupl2(m):
    '1I'

    if 'idxs' not in m:
        m['idxs'] = [(i, m['i']) for i in range(m['i'], m['Nb'])]\
            + [(m['i'], i) for i in range(m['j']+1, m['i']+1)]

    msg = m.copy()
    msg['i'], msg['j'] = m['idxs'].pop()
    msg['ii'] = m['i']
    del msg['idxs']

    return ('continue' if m['idxs'] else 'terminate',
            {0: [msg]},
            m if m['idxs'] else None)


s_join = '''
synch join (_1, _2 | _1)
{
  store acc;

  start {
    on:
      _1.(Lij) {
        set acc = this;
        goto second;
      }

      _1.@_ {
        send this => _1;
      }
  }

  second {
    on:
      _2.(Aij) {
        send {acc || this} => _1;
        goto start;
      }
  }
}
'''


s_join2 = '''
@i
@j
synch join2 (lik, aij | aij)
{
  store acc1;
  store acc2;

  start {
    on:
      lik.(Lij, ii) & [i==j] {
        set acc1 = (Lik: Lij);
        goto second;
      }


    elseon:
      lik.(Lij, ii) & [ii == i] {
        set acc1 = (Lik: Lij);
        goto second;
      }

      lik.(Lij, ii) & [ii == j] {
        set acc2 = (Ljk: Lij);
        goto second;
      }
  }

  second {
    on:
      lik.(Lij, ii) & [i==j] {
        set acc2 = (Ljk: Lij);
        goto third;
      }

    elseon:
      lik.(Lij, ii) & [ii == i] {
        set acc1 = (Lik: Lij);
        goto third;
      }

      lik.(Lij, ii) & [ii == j] {
        set acc2 = (Ljk: Lij);
        goto third;
      }
  }

  third {
    on:
      aij.(Aij) {
        send {acc1 || acc2 || this} => aij;
        goto start;
      }
  }
}
'''

s_cnt = '''
synch cnt (_1, _2 | _1, _2, _3)
{
  state int(32) c = 0, cc = 0;

  start {
    on:
      _1.(Aij) {
        set c = [c+1];
        send this => _1;
      }

      _1.@_ {
        set cc = [c], c = [0];
        send (this || c: cc) => _3;
      }


      _2.(Lij) {
        send this => _2;
      }

      _2.@_ {
      }
  }
}
'''


s_segm = '''
synch segm (_1, _2 | _1)
{
  state int(32) cc = 0;
  state int(32) limit = 0;
  state int(32) seg = 0;

  start {
    on:
      _1.(Aij) & [limit == 0 || cc < limit] {
        set cc = [cc+1];
        send this => _1;
      }

      _1.(Aij) & [limit > 0 && cc == limit - 1] {
        set limit = [0], cc = [0];
        send this => _1, @[seg] => _1;
      }

      _2.@d(c) {
        set limit = [c], seg = [d];
      }
  }
}
'''

#------------------------------------------------------------------------------

s_ResultFilter = '''
synch ResultFilter (_1 | _1)
{
  state int(32) cc = 0;

  start {
    on:
      _1.(Nb) & [cc < ((Nb*Nb - Nb)/2 + Nb)-1] {
        set cc = [cc+1];
        send this => _1;
      }

      _1.(Nb) & [cc == ((Nb*Nb - Nb)/2 + Nb)-1] {
        set cc = [0];
        send this => _1, @[0] => _1;
      }

      _1.@_ {}
  }
}
'''

#------------------------------------------------------------------------------
# Mergers


s_MergeSwitch = '''
synch MergeSwitch (a:k, b:k | c:k)
{
  start {
    on:
      a.() {
        send this => c;
        goto s_a;
      }

      b.() {
        send this => c;
        goto s_b;
      }

      a.@_ { }
      b.@_ { }
  }

  s_a {
    on:
      a.() {
        send this => c;
      }

      a.@_ {
        send this => c;
        goto start;
      }
  }

  s_b {
    on:
      b.() {
        send this => c;
      }

      b.@_ {
        send this => c;
        goto start;
      }
  }
}
'''


#------------------------------------------------------------------------------

def c_ResultCombiner(ma, mb):
    '1MO'
    import numpy as np

    if 'cols' not in ma:
        ma['Nc'], ma['Nz'] = 1, 0
        ma['cols'] = []
        ma['blocks'] = {ma['i']: ma['Lij']}

    ma['blocks'][mb['i']] = mb['Lij']
    ma['Nc'] += 1

    if not ma['Nc'] % ma['Nb']:
        col = np.vstack([ma['blocks'][i] for i in range(ma['Nb'])])
        ma['cols'].append(col)

        ma['blocks'].clear()
        ma['Nz'] += 1

        for i in range(ma['Nz']):
            ma['blocks'][i] = np.zeros(mb['Lij'].shape)
            ma['Nc'] += 1

        if len(ma['cols']) == ma['Nb']:
            ma['A'] = np.hstack(ma['cols'])
            del ma['cols']
            del ma['blocks']

    return ('partial', {},
            ma if (ma['Nc'] < ma['Nb'] * ma['Nb']) else {'A': ma['A']})

#------------------------------------------------------------------------------

import numpy as np


m, n = 16, 128
A = np.load('spd_%dx%d.dmp' % (m, n))

__input__ = {'in': [
    comm.Record({'A': A, 'Nb': m}),
    comm.SegmentationMark(0)
]}


def __output__(stream):
    '1H'

    import numpy as np
    import time

    for i, ch, msg in stream:
        content = msg.content

        arrays = [k for k, v in content.items() if type(v) == np.ndarray]
        for k in arrays:
            content[k] = content[k].shape

        print(time.time(), 'O: %s: %s' % (ch, content))

import astrakahn
astrakahn.start()
