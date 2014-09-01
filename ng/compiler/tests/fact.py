'''
net Factorial (in | out)
connect
  <in|Test|out,init,n> .. <n|Gen|terms> .. <init,terms|Reduce|out>
end
'''

def Test(n):
    '3T'
    pass

def Gen(n):
    '1I'
    pass

def Reduce(init, terms):
    '1DU'
    pass
