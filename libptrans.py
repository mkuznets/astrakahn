from compiler.sync.compiler import parse
from compiler.sync.backend import SyncBuilder

def build_guard(n_out):

    s___R__ = '''
    synch Guard (in, __fb__ | r, __sl__)
    {
      state int(32) seg_len;
      state int(32) cnt;

      start {
        on:
          in.@depth {
            send (d: depth || l: seg_len) => __sl__;
            goto wait_feedback;
          }

          in.else {
            set seg_len = [seg_len + 1];
            send this => r;
          }
      }

      wait_feedback {
        on:
          __fb__ & [cnt < NOUT] {
            set cnt = [cnt + 1];
          }

          __fb__ & [cnt == NOUT - 1] {
            set seg_len = [0], cnt = [0];
            goto start;
          }
      }
    }
    '''

    ast = parse(s___R__, {'NOUT': n_out})
    sb = SyncBuilder()
    return sb.traverse(ast)


def build_collector():

    s___C__ = '''
    synch Collector (__mrg__, __sl__ | out, __fb__)
    {
      state int(32) seg_len, exp_len, depth;

      start {
        on:
          __mrg__ & [seg_len == (exp_len - 1)] {
            set seg_len = [0], exp_len = [-1];
            send this => out,
                 @depth => out,
                 (confirm : [1]) => __fb__;
          }

          __mrg__.else {
            set seg_len = [seg_len + 1];
            send this => out;
          }

          __sl__.(d, l) & [seg_len == l] {
            set seg_len = [0], exp_len = [-1];
            send @d => out,
                 (confirm : [1]) => __fb__;
          }

          __sl__.(d, l) & [seg_len < l]  {
            set exp_len = [l], depth = [d];
          }
      }
    }
    '''

    ast = parse(s___C__)
    sb = SyncBuilder()

    return sb.traverse(ast)
