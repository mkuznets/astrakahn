'''
net pic (in | out)
  net pic_step (in | out)
    morph calc_density (N) { }
    morph solve_poisson (N) { }
    morph calc_fields (N) { }
    morph interpolate_fields (N) { }
    morph move_particles (N) { }
    synch zip2 (1, 20)
  connect
    calc_density
     .. (solve_poisson)*
     .. calc_fields
     .. interpolate_fields
     .. move_particles
  end
connect
  (pic_step)*
'''
