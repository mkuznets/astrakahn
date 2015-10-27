#!/usr/bin/env python3

import os
import sys
import inspect
import hashlib
from network import Network
from multiprocessing import cpu_count

import compiler.net as compiler


def __output__(stream):
    '''
    1H
    '''
    import time

    for entry in stream:
        pid, pname, msg = entry
        print(time.time(), 'O: %s: %s' % (pname, msg))


def get_caller_module():

    from os.path import dirname, basename, abspath, basename, splitext

    caller = inspect.stack()[3]
    path = dirname(abspath(caller[1]))
    filename = caller[1]
    name = splitext(basename(caller[1]))[0]

    return name, filename, path, caller[0].f_globals


def get_net():

    name, filename, path, caller = get_caller_module()

    ## Load runtime component network from cache.
    #rt_file = os.path.join(path, '%s.rt' % name)

    #src_hash = hashlib.md5(open(filename, 'rb').read()).hexdigest()

    #if (os.path.isfile(rt_file) and os.access(rt_file, os.R_OK)):
    #    obj = load(input_file=rt_file)

    #    if type(obj) == tuple and len(obj) == 2 and obj[1] == src_hash:
    #        return obj[0]


    # Extract network code from module docstring.
    code = caller['__doc__']

    # Extract definitions of core functions and synchronisers.
    cores = {n[2:]: g for n, g in caller.items()\
             if inspect.isfunction(g) and n.startswith('c_')}

    syncs = {n[2:]: g for n, g in caller.items()\
             if type(g) is str and n.startswith('s_')}

    # Add handler function to core function list.
    is_custom_handler = inspect.isfunction(caller.get('__output__'))
    handler = caller['__output__'] if is_custom_handler else __output__
    cores['__output__'] = handler

    # Compile network.
    net_comp = compiler.compile(code, cores, syncs)
    net = Network(net_comp, nproc=4)

    # If initial input is defined, send it to network.
    if isinstance(caller.get('__input__'), dict):
        net.init_input(caller['__input__'])

    if caller.get('__profile__'):
        with open(caller.get('__profile__'), 'rb') as p:
            import pickle
            profile = pickle.load(p)

            for vid, prof in profile.items():
                if prof < 0.8:
                    print('Disable ext run:', vid)
                    vertex = net.get_by_path(vid)
                    vertex.run_ext = False

    ## Save compiled network to cache file.
    #dump(net, src_hash, os.path.join(path, '%s.rt' % name))

    net.show()
    print()

    return net


def start():
    net = get_net()
    #net.run()


def dump(network, hash, output_file=None):
    import dill
    import marshal

    obj = (network, hash)

    # Dump core functions to allow the Network object to be serialized.
    for n in network.network.nodes():
        obj = network.node(n)['obj']
        if hasattr(obj, 'core') and obj.core is not None:
            name = obj.core.__name__
            obj.core = (name, marshal.dumps(obj.core.__code__))

    if output_file is None:
        return dill.dumps(obj)
    else:
        dill.dump(obj, open(output_file, 'wb'))


def load(data=None, input_file=None):
    import dill
    import marshal
    import types

    if data is not None:
        obj = dill.loads(data)
    elif input_file is not None:
        obj = dill.load(open(input_file, 'rb'))
    else:
        raise ValueError('Either object or input file must be specified.')

    # Deserialize functions' code.
    #for n in network.network.nodes():
    #    obj = network.node(n)['obj']
    #    if hasattr(obj, 'core') and obj.core is not None:
    #        code = marshal.loads(obj.core[1])
    #        obj.core = types.FunctionType(code, globals(), obj.core[0])

    return obj
