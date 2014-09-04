'''
net Factorial (in | out)
connect
  <in|Test|out,init,n> .. <n|Gen|terms> .. <init,terms|Reduce|out>
end
'''


def Test(n):
    '3T'
    if n <= 1:
        return ('send', {0: n}, None)
    else:
        return ('send', {1: 1, 2: n}, None)


def Gen(n):
    '1I'
    if n == 1:
        return ('terminate', {}, None)
    else:
        sn = n
        n -= 1
        return ('continue', {0: sn}, n)


def Reduce(a, b):
    '1DU'
    c = a * b
    return ('partial', {}, c)
