from boxes import *

__input__ = {'in': [1]}


def __output__(channel, msg):
    pass

@inductor(1)
def splitter(m):
    import numpy as np
    from collections import deque

    if 'blocks' not in m:
        blocks = deque()

        bsz = m['d'] // m['Nb']

        for i in range(m['Nb']):
            for j in range(i+1):
                sl = (slice(i*bsz, (i+1)*bsz), slice(j*bsz, (j+1)*bsz))
                A = m['A'].copy()
                A[sl]
                blocks.append({'Nb': m['Nb'], 'i': i, 'j': j, 'Aij': A})

        m['blocks'] = blocks

    msg = m['blocks'].popleft()

    #print('Coord', msg['i'], msg['j'])

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

@transductor(2)
def InitFact(m):
    import numpy as np

    sAij = m['Aij']
    Aij = sAij.open()

    t = np.linalg.cholesky(Aij)
    Aij[:][:] = t

    # Clean up shared object.
    del Aij
    sAij.close()

    m['Lij'] = sAij
    del m['Aij']
    m['Nr'] = m['Nb'] - m['i'] - 1

    r = {'Lij': sAij, 'Nb': m['Nb'], 'i': m['i'], 'j': m['j']}
    return ('send', {0: [m], 1: [r]}, None)

@transductor(2)
def TrigSolve(m):
    import numpy as np

    sAij, sLij = m['Aij'], m['Lij']
    Aij, Lij = sAij.open(), sLij.open()

    t = np.dot(Aij, np.linalg.inv(Lij.T))
    Aij[:][:] = t

    # Clean up shared object.
    del Aij, Lij
    sAij.close()
    sLij.close()

    m['Nr'] = m['Nb']
    m['Lij'] = sAij
    del m['Aij']

    r = {'Lij': sAij, 'Nb': m['Nb'], 'i': m['i'], 'j': m['j']}
    return ('send', {0: [m], 1: [r]}, None)


@transductor(1)
def SymRank(m):
    import numpy as np

    sAij, sLik, sLjk = m['Aij'], m['Lik'], m['Ljk']
    Aij, Lik, Ljk = sAij.open(), sLik.open(), sLjk.open()

    t = Aij - np.dot(Lik, Ljk.T)
    Aij[:][:] = t

    del Aij, Lik, Ljk
    sAij.close()
    sLik.close()
    sLjk.close()

    del m['Lik'], m['Ljk']
    return ('send', {0: [m]}, None)


@inductor(1)
def dupl(m):
    if m['Nr'] <= 0:
        return ('terminate', {}, None)

    m['Nr'] -= 1
    msg = m.copy()
    msg['Lij'] = m['Lij'].copy()
    del msg['Nr']

    return ('continue', {0: [msg]}, m)


@inductor(1)
def dupl2(m):

    if 'idxs' not in m:
        m['idxs'] = [(i, m['i']) for i in range(m['i'], m['Nb'])]\
            + [(m['i'], i) for i in range(m['j']+1, m['i']+1)]

    msg = m.copy()
    msg['Lij'] = m['Lij'].copy()

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

@reductor(MONADIC, ORDERED, 1)
def ResultCombiner(ma, mb):

    import numpy as np

    if 'blocks' not in ma:
        ma['blocks'] = set((i, j) for i in range(ma['Nb']) for j in range(i+1))
        ma['blocks'].remove((ma['i'], ma['j']))


    ma['blocks'].remove((mb['i'], mb['j']))

    if not ma['blocks']:
        ma['Lij'].key = None

        A = ma['Lij'].open()
        A[:][:] = np.tril(A)

        del A
        ma['Lij'].close()

        return ('partial', {}, {'A': ma['Lij']})

    else:
        return ('partial', {}, ma)
