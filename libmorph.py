from compiler.sync.compiler import parse
from compiler.sync.backend import SyncBuilder

def build_marker():

    s_Marker = '''
    synch Marker (in, __nfrag__, __refrag__ | out)
    {
      state int(32) nfrag = 10, ntmp=10,
                    refrag = 0, refragtmp = 0;

      start {
        on:
          in.@d {
            set nfrag = [ntmp], refrag = [refragtmp];
            send this => out;
          }

        elseon:
          in & [refrag] {
            send (__nfrag__: nfrag || 'refrag || this) => out;
          }

          in.else {
            send (__nfrag__: nfrag || this) => out;
          }

          __nfrag__.(n) {
            set ntmp = [n];
          }

          __refrag__.(r) {
            set refragtmp = [r];
          }
      }
    }
    '''

    ast = parse(s_Marker)
    sb = SyncBuilder()
    return sb.traverse(ast)


def build_router(n_over):

    s_Router = '''
    synch Router (in %s | out, _out %s)
    {
      state int(1) last = 0;

      start {
        on:
          in.@d & [last == 0] {
            send this => out;
          }

          in.@d & [last == 1] {
            send this => _out;
          }

        elseon:
          in.(refrag) & [refrag == 0] {
            set last = [0];
            send this => out;
          }

          in.(refrag) & [refrag == 1] {
            set last = [1];
            send this => _out;
          }

        elseon:
          in {
            # Default destination: to refragmentation.
            set last = [0];
            send this => out;
          }

          %s
      }
    }
    '''

    ports = (', ' + ', '.join(['_over%d' % i for i in range(n_over)])) if n_over else ''
    states_code = "\n\n".join(["_over%d & [last == 1] { send this => _over%d; }" % (i, i) for i in range(n_over)]) if n_over else ''

    s_Router = s_Router % (ports, ports, states_code)

    ast = parse(s_Router)
    sb = SyncBuilder()
    return sb.traverse(ast)
