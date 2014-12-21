#!/usr/bin/env python3

'''
net NetWithStar (a| a)

  net fps_test (a| a, __output__)
    synch fps_begin [FPS_PORT=a, STAGE_IN=in]
    synch fps_end [FPS_PORT=a, STAGE_OUT=out]
  connect
    fps_begin.. <in|Test|out> .. fps_end
  end

  connect
    (fps_test)*
end
'''


import communication as comm


def c_Test(m):
    '1T'
    a = m['a']
    mc = m.copy()

    mc['a'] += 1

    if 'n' not in mc:
        mc['n'] = 1
    else:
        mc['n'] += 1

    if mc['n'] == 5:
        mc['ffp'] = True

    return ('send', {0: mc}, None)


__input__ = {'a': [
    comm.Record({'i': 0, 'a': 0}),
    comm.Record({'i': 1, 'a': 1}),
    comm.Record({'i': 2, 'a': 2, 'rfp': True}),
]}

for i in range(3, 100):
    __input__['a'].append(comm.Record({'i': i, 'a': 0}))


import astrakahn
astrakahn.start()
