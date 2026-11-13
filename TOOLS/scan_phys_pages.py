#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-16: карта физических страниц ядра core-pc.bin (k46-core411)
и поиск сигнатур МОНЫ-80: Э62 5747(М12) = 0o61445747 (вирт. 00421),
atx 10003(16) - билдер 06210, rte-77 03663."""
import sys

CORE = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/z/my-project/re-glissade/RUNS/run-2026-11-13g/k46-core411/core-pc.bin'
data = open(CORE, 'rb').read()
N = len(data) // 6
words = [int.from_bytes(data[i*6:(i+1)*6], 'big') for i in range(N)]

print('== Карта ненулевых физических страниц (256 слов) ==')
runs = []
for p in range(N // 256):
    nz = sum(1 for w in words[p*256:(p+1)*256] if w)
    if nz:
        runs.append((p, nz))
# сжать подряд идущие
seg = []
for p, nz in runs:
    if seg and p == seg[-1][1] + 1:
        seg[-1][1] = p
        seg[-1][2] += nz
    else:
        seg.append([p, p, nz])
for p0, p1, nz in seg:
    print(f'  физ.стр {p0:03o}-{p1:03o} (адр {p0*256:05o}-{p1*256+255:05o}): {nz} слов')

print('\n== Сигнатура Э62 5747(М12) = 0o61445747 ==')
for i, w in enumerate(words):
    if w == 0o61445747:
        print(f'  физ.{i:05o}')
