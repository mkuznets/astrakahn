net Cholesky (in | result)
  synch Router
  synch join
  synch cnt
  synch segm
  synch MergeSwitch
  synch ResultFilter
  tab [i, j] synch join2
connect
  <in|splitter|iblocks>
  .. (<iblocks, cblocks|MergeSwitch|blocks>
       .. <blocks|Router|akk,aik,aij>
       .. <akk|InitFact|_1,result> .. dupl|lkk> .. <lkk,aik|join
       .. TrigSolve|_1,result> .. dupl2|lik> .. <aij,lik|cnt|aij,lik,sg> .. join2 .. <aij,sg|segm
       .. SymRank|cblocks>
     ) \ .. <result|ResultFilter .. ResultCombiner|result>
end
