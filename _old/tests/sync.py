#!/usr/bin/env python3

variables = {'state': [], 'store': ['ma', 'mb']}

zip2 = {
    'start': {
        0: {
            'group': [{'type': 'on', 'segmark': None, 'pattern': None,
                       'exec': {'send': None,
                                'assign': [('ma', ('__this__'))],
                                'goto': ['s1']}
                       }
                      ],
            'else': None
        },

        1: {
            'group': [{'type': 'on', 'segmark': None, 'pattern': None,
                       'exec': {'send': None, 'goto': ['s2'],
                                'assign': [('mb', ('__this__'))]
                                }
                       }
                      ],
            'else': None
        },
    },

    's1': {
        1: {
            'group': [{'type': 'on', 'segmark': None, 'pattern': None,
                       'exec': {
                           'send': {
                               0: [{'segmark': None, 'pattern': ('ma', ('__this__')), 'choice': None}]
                           },
                           'assign': None, 'goto': ['start']}
                       }
                      ],
            'else': None
        },
    },

    's2': {
        0: {
            'group': [{'type': 'on', 'segmark': None, 'pattern': None,
                       'exec': {
                           'send': {
                               0: [{'segmark': None, 'pattern': ('mb', ('__this__')), 'choice': None}]
                           },
                           'assign': None, 'goto': ['start']}
                       }
                      ],
            'else': None
        },
    },
}


