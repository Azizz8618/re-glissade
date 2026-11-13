#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поиск аутентичных лист-заголовков (0o22015 + веса VGR) на дисковых образах.
zone_t = uint64 conv[8] + uint64 data[1024] (big-endian 6-байт слова)."""
import sys
import struct

HEADER0 = 0o0000000000022015
VES = [0o6400000000000000, 0o6000000000000000, 0o5400000000000000,
       0o5000000000000000, 0o4400000000000000, 0o4000000000000000]

def zones(path):
    data = open(path, 'rb').read()
    zs = 64 + 1024 * 6
    n = len(data) // zs
    for z in range(n):
        off = z * zs + 64
        words = [int.from_bytes(data[off + i*6: off + i*6 + 6], 'big')
                 for i in range(24)]
        yield z, words

def iso_str(v):
    b = [(v >> s) & 0xFF for s in (40, 32, 24, 16, 8, 0)]
    return ''.join(chr(x) if 32 <= x < 127 else '.' for x in b)

def main():
    for path in sys.argv[1:]:
        data = open(path, 'rb').read()
        zs = 64 + 1024 * 6
        n = len(data) // zs
        print(f'=== {path}: {n} зон ===')
        for z in range(n):
            off = z * zs + 64
            words = [int.from_bytes(data[off + i*6: off + i*6 + 6], 'big')
                     for i in range(24)]
            # критерии: сл.0 = 0o22015 или веса на сл.1-6
            if words[0] == HEADER0 or all(words[i+1] in VES for i in range(3)):
                print(f'-- зона {z} (0o{z:04o}):')
                for i, w in enumerate(words):
                    print(f'   [{i:02o}] {w:016o}  {iso_str(w)}')

if __name__ == '__main__':
    main()
