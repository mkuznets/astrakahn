sync throttle [per] (a:0 | b:0)
{
  state int(8) val;

  start:
    do val := 0
    goto work;

  work:
    on a.(v) && (val + v >= per)
    send (v := val + v) => b
    goto start;

    on a.(v) && (val + v < per)
    do val := val + v
    goto work;

    on a.else
    goto work;
}
