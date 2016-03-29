#!/usr/bin/env python3

import inspect
import os
from typing import Callable


def is_box(f: Callable) -> bool:
    return inspect.isfunction(f) and hasattr(f, '__box__')


def is_file_readable(filename: str) -> bool:
    return os.path.isfile(filename) and os.access(filename, os.R_OK)
