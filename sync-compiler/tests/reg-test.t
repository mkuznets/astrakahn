sync id [w,e,q] (c : 0, b : s, a : 0 | f : 0, c : 0)
{
  store msg: a, msg_1: b; 
  state enum (f,d) g;
  state int (8) j, h;
  state int (2) b;

start:
  on a.@p && (h + j)
  do h := 1, j := 2
  send (v := p + p) => b
  goto w;

  on a.else && (h * (j + 1))
  do h := (b + j)
  goto start;

w:
  on b.(c,c_1)
  ;

  on c.?v
  send (msg, this) => f, this => c
  goto w,start;

  on c.?c(kk)
  do b := 1;
}
