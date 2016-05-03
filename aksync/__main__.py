import os
import stat
from optparse import OptionParser
from .compiler import compile

usage = "usage: %prog [options] file"
opts = OptionParser(usage=usage)

opts.add_option('-o', '--output', type='string', dest='output',
                metavar='OUTPUT', default='a.py')
opts.add_option('-p', '--nproc', type='int', dest='np', metavar='NPROC',
                default=1)
opts.add_option('-d', action='store_true', dest='debug', default=False)


if __name__ == '__main__':

    (options, args) = opts.parse_args()

    if len(args) != 1:
        opts.error('Input file is required')

    filename = args[0]

    if not os.path.isfile(filename) or not os.access(filename, os.R_OK):
        opts.error('Input file does not exist or cannot be read')

    with open(filename, 'r') as f:
        output = compile(f.read())

    with open(options.output, 'w') as f:
        f.write(output)

        mode = os.fstat(f.fileno()).st_mode
        mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        os.fchmod(f.fileno(), stat.S_IMODE(mode))
