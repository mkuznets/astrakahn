net pic_step (in | out)

  net bar (g | p)
    morph calc (N) {div / [mover_one, mover_two] / joiner}
  connect
    (calc || k .. a* || c\)*
  end

  morph move_particles (N) {div / [mover_one / joiner, mover_two / joiner]}

connect

end
