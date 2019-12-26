net Foo (_1 | r1)
  sync zip [CONST=104]
connect
  gen .. foo|a, b> .. zip .. <a|bar .. summ|r1>

  #gen .. bar .. summ|r1>
end
