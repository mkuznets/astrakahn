#!/usr/bin/env python3

def is_namedtuple(x):
    t = type(x)
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple):
        return False
    return all(type(n)==str for n in f)


def rprint(obj, offset=0):

    if is_namedtuple(obj):
        print(type(obj).__name__)
        offset += 2

        names = obj._fields
        maxlen = max(map(len, names))

        for n in obj._fields:
            left_border = maxlen + 2
            n_spaces = left_border - len(n)

            print((' ' * offset) + n + ':' + (' ' * n_spaces), end='')
            item = obj.__getattribute__(n)
            rprint(item, left_border + offset + 1)
        print()

    elif type(obj) == list:
        if sum(map(len, (str(i) for i in obj))) < 80:
            print(obj)
            return

        item_offset = offset + 2

        print('[')

        for item in obj:
            print((' ' * item_offset), end='')
            rprint(item, item_offset)

        print((' ' * offset) + ']')

    else:
        print(str(obj))
