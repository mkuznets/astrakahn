import collections


class Variable:

    def __init__(self, name):
        self.name = name
        self.value = None

    def get(self):
        return self.value

    def set(self):
        raise NotImplemented('Set method not implemented for abstract type.')


class StateInt(Variable):

    def __init__(self, name, width):
        super(StateInt, self).__init__(name)
        self.width = width
        self.value = 0

    def set(self, value):
        if value > 0 and value <= 2 ** self.width:
            self.value = value
        else:
            raise RuntimeError('Value is out of range.')

    def __repr__(self):
        return 'StateInt({})'.format(self.width)


class StateEnum(Variable):

    def __init__(self, name, values):
        super(StateEnum, self).__init__(name)
        self.values = list(values)

    def set(self, value):
        if value in self.values:
            self.value = value
        else:
            raise RuntimeError('Value is out of range.')

    def __repr__(self):
        return 'StateEnum({})'.format(self.values)


class StoreVar(Variable):

    def __init__(self, name, channel):
        super(StoreVar, self).__init__(name)
        self.channel = channel

    def set(self, value):
        self.value = value

    def __repr__(self):
        return 'StoreVar({})'.format(self.channel)


State = collections.namedtuple('State', 'on elseon')
TransitionSet = collections.namedtuple('TransitionSet', 'group dotelse')
Transition = collections.namedtuple('Transition', 'condition guard actions')
Actions = collections.namedtuple('Actions', 'assign send goto')


def build(sync_ast):

    automata = {}
    store_vars = {}
    state_vars = {}

    # Transform variables declarations.
    for decl in sync_ast['decls']:
        # decl = (state|store, type, [var1, var2, ...)

        if decl[0] == 'store':
            for name, channel in decl[2]:
                store_vars[name] = StoreVar(name, channel)

        elif decl[0] == 'state':
            var_type = decl[1]
            if var_type[0] == 'int':
                for name in decl[2]:
                    state_vars[name] = StateInt(name, var_type[1])
            elif var_type[0] == 'enum':
                for name in decl[2]:
                    state_vars[name] = StateEnum(name, var_type[1])
            else:
                raise ValueError('Wrong type of variable.')
        else:
            raise ValueError("Variable can be `state' or `store' only.")

    # Transform AST.
    for state_name, transitions in sync_ast['trans'].items():

        if state_name not in automata:
            automata[state_name] = State({}, {})
        state_obj = automata[state_name]

        for trans in transitions:
            on = trans['on']
            channel, condition, guard = on[1]

            # Choose proper transition dict: `on' or 'elseon':
            trans_dict = state_obj[0] if on[0] == 'on' else state_obj[1]

            # Add new channel to transition dict
            if channel not in trans_dict:
                trans_dict[channel] = TransitionSet([], None)

            actions = Actions(trans['do'], trans['send'], trans['goto'])

            transition = Transition(condition, guard, actions)

            if condition == '__else__':
                if trans_dict[channel].dotelse is not None:
                    raise ValueError('More than one .else statements are not '
                                     'allowed.')
                # Replace the whole set: group is the same, dotelse is set now.
                trans_group = trans_dict[channel].group
                trans_dict[channel] = TransitionSet(trans_group, transition)
            else:
                # Simply add new transition to the group.
                trans_dict[channel].group.append(transition)

    return (automata, store_vars, state_vars)


def pretty_print(ir):

    for c, t in ir[0].items():
        print(c)

        print('on')
        for i, p in t[0].items():
            print(i, p)

        print('elseon')
        for i, p in t[1].items():
            print(i, p)
        print()

    print(ir[1])
    print(ir[2])
