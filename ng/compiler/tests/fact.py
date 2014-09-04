'''
net Factorial (in | out)
connect
  <in|Test|out,init,n> .. <n|Gen|terms> .. <init,terms|Reduce|out>
end
'''

def Test(n):
    '3T'
    print('fsfasf')

def Gen(n):
    '1I'
    pass

def Reduce(init, terms):
    '1DU'
    pass

#import copy

#def printer(d):
#    print(d)
#    return ('send', {}, None)
#
#
#def foo(n):
#    n += 1
#    return ('send', {0: {'value': n, 'n': 10}}, None)
#
#
#def plus(a, b):
#    c = a + b
#    return ('partial', {}, c)
#
#
#def cnt(s):
#    if s['n'] == 0:
#        return ('terminate', {}, None)
#
#    #time.sleep(2)
#    cont = copy.copy(s)
#    cont['value'] += 1
#    cont['n'] -= 1
#
#    return ('continue', {0: s['value']}, cont)
