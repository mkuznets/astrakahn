#!/usr/bin/env python3

zip2 = {
    'start': {
        0: {
            'group': [{'type': 'on',
                       'segmark': None,
                       'pattern': None,
                       'choice': None,
                       'exec': {'send': None,
                                'assign': ('global', 'ma', '__this__'),
                                'goto': ['s1']}
                       }
                      ],
            'else': None
        },

        1: {
            'group': [{'type': 'on',
                       'segmark': None,
                       'pattern': None,
                       'choice': None,
                       'exec': {'send': None,
                                'assign': ('global', 'mb', '__this__'),
                                'goto': ['s2']}
                       }
                      ],
            'else': None
        },
    },

    's1': {
        1: {
            'group': [{'type': 'on',
                       'segmark': None,
                       'pattern': None,
                       'choice': None,
                       'exec': {
                           'send': {
                               0: [{'segmark': None, 'pattern': '(ma, __this__)', 'choice': None}]
                           },
                           'assign': None,
                           'goto': ['start']}
                       }
                      ],
            'else': None
        },
    },

    's2': {
        0: {
            'group': [{'type': 'on',
                       'segmark': None,
                       'pattern': None,
                       'choice': None,
                       'exec': {
                           'send': {
                               0: [{'segmark': None, 'pattern': '(mb, __this__)', 'choice': None}]
                           },
                           'assign': None,
                           'goto': ['start']}
                       }
                      ],
            'else': None
        },
    },
}


