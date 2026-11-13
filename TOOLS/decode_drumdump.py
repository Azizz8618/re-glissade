#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Декодирование drum_dump dispak: строка = "к LLL, RRR ; ДАННЫЕ ; ADDR".
import sys
sys.path.insert(0, '/home/z/my-project/re-glissade/TOOLS')
from parse_dd import gost_str

path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/k46print/dd.m20'
z0 = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
z1 = int(sys.argv[3], 0) if len(sys.argv) > 3 else 8
words = {}
for line in open(path, encoding='utf-8', errors='replace'):
    line = line.strip()
    if not line or line.startswith('в '):
        continue
    parts = line.split(';')
    if len(parts) < 3:
        continue
    try:
        addr = int(parts[2].strip(), 8)
    except ValueError:
        continue
    digits = ''.join(ch for ch in parts[1] if ch in '01234567 ')
    octs = digits.split()
    w = 0
    for o in octs[:4]:
        w = (w << 12) | int(o, 8)
    words[addr] = w

print("всего слов: %d, зона %o-%o" % (len(words), z0, z1 - 1))
for base in range(z0 * 1024, z1 * 1024, 8):
    row = [words.get(a, 0) for a in range(base, base + 8)]
    if not any(row):
        continue
    g = ' | '.join(gost_str(w) for w in row)
    print("  %05o: %s" % (base, g))
