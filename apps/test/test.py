from akc.boxes import *

@transductor(1)
def bar(m):
    r = m ** 2
    return (r, )

@inductor(1)
def gen(m):
    r = m+1
    gen.cont = r if r < 10 else None
    return (r, )

@reductor(MONADIC, UNORDERED, 1)
def summ(m):
    if summ.cont is None:
        summ.cont = 0
    summ.cont = m + summ.cont

@transductor(2)
def foo(m):
    r1 = m - 1
    r2 = m + 1
    return (r1, r2)

def __output__(channel, msg):
    print(channel, msg)

__input__ = {
    '_1': [[1, 2, 3], [4, 5, 6]]
    #'_1': [5]
}
