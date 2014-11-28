'''
net foo (i1 | i2, i3)
  morph (nn) {
    div / b1, b2 / joiner
  }

  morph (nn) {
    div / b1, b2 / joiner,
    (aa / bb, cc / dd) / ee,
    zz / (yy / xx, ww / vv)

    where ee .. zz = fff
  }

  morph (lllll) {
    (aa / bb, cc / dd) / ee

    where joiner .. div = glue,
          aa .. cc = fff,
          aa .. zz = aaa
  }

  synch FOO
  synch BAR [TRUE=FALSE, good=bad] ["/home/mkuznets"]

  net bar (g1, g2, g3 | p1)
    morph (N) {a / b / c}
  connect
    (a .. b .. (a)) .. b || c || (d* .. d\)* .. e*
  end

  morph (N) {div / (mover_one / joiner, mover_two / joiner)}

connect
  ((f*) .. g)*\ .. d\* .. ( a .. b || c .. d)
end
'''
