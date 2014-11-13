#!/usr/bin/env python3

from components import *
from compiler.sync import parse as sync_parse
from . import ast


class NetBuilder(ast.NodeVisitor):
    pass
