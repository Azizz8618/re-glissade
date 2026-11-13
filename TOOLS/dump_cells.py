#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Печать слов дампа ядра (65536 x 6B BE) в восьмеричном виде.

Использование: dump_cells.py <core.bin> <начало-восьм.> <конец-восьм.> [...]
"""
import sys


def words(path):
    with open(path, 'rb') as f:
        b = f.read()
    return [int.from_bytes(b[i * 6:(i + 1) * 6], 'big')
            for i in range(len(b) // 6)]


def main():
    w = words(sys.argv[1])
    args = [int(x, 8) for x in sys.argv[2:]]
    for lo, hi in zip(args[0::2], args[1::2]):
        print(f'--- {lo:05o}-{hi:05o} ---')
        for a in range(lo, hi):
            print(f'{a:05o}: {w[a]:016o}')


if __name__ == '__main__':
    main()
