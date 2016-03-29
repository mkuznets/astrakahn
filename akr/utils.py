from typing import Iterable


def partition(lst: Iterable, n: int) -> list:
    lst = list(lst)
    return [lst[i::n] for i in range(n)]


import hashlib

def md5i(n: int, p: int) -> int:
    nb = (n + p).to_bytes(16, 'little')
    h = hashlib.md5(nb).digest()
    return int.from_bytes(h, 'little')

def md5s(s: bytes, p: int) -> int:
    sp = s + p.to_bytes(16, 'little')
    h = hashlib.md5(sp).digest()
    return int.from_bytes(h, 'little')

def to_bytes(n: int) -> bytes:
    return n.to_bytes(16, 'little')
