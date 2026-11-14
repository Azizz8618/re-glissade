#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-17: декод ВСЕХ зон файла печати из dd.m20 (барабан 020).

Формат dd.m20: 'к <октеты>; с <октеты>; <адрес>' - адрес = тракт*1024+слово.
Печать-файл МОНЫ-80: ISO-8бит, байт 0o200+N = N пробелов (RLE), EOR 0o12.

Использование: decode_print_glis1r.py <dd.m20> [зона-начала] [зона-конца]
"""
import sys

path = sys.argv[1]
z0 = int(sys.argv[2], 8) if len(sys.argv) > 2 else 0
z1 = int(sys.argv[3], 8) if len(sys.argv) > 3 else 0o40

words = {}
for line in open(path, encoding='utf-8', errors='replace'):
    if not line.startswith('к '):
        continue
    parts = line.split(';')
    if len(parts) < 3:
        continue
    try:
        addr = int(parts[2].strip(), 8)
    except ValueError:
        continue
    octs = [o for o in ''.join(ch for ch in parts[1] if ch in '01234567 ').split()]
    w = 0
    for o in octs[:4]:
        w = (w << 12) | int(o, 8)
    words[addr] = w

data = bytearray()
for a in sorted(words):
    if not (z0 * 1024 <= a < z1 * 1024):
        continue
    w = words[a]
    data += bytes((w >> s) & 0xFF for s in (40, 32, 24, 16, 8, 0))

out, cur = [], bytearray()
for b in data:
    if b >= 0o200:
        cur += b' ' * (b - 0o200)
    elif b == 0o12:
        out.append(bytes(cur)); cur = bytearray()
    elif b == 0:
        if cur:
            out.append(bytes(cur)); cur = bytearray()
    else:
        cur.append(b)
for i, ln in enumerate(out):
    try:
        print('%4d|%s' % (i, ln.decode('iso-8859-5')))
    except Exception:
        print('%4d|%r' % (i, ln))
