#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-16(2): поиск билдера МОНЫ в физическом ядре:
- atx 1(1)  = 0o1000001 (вирт. 06232, финальная запись [11043]:=6)
- все atx X(16): (half & 0o77700000)==0o70000000, X=half&0o7777
Контекст кандидатов - дизассемблирование."""
import sys

CORE = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/z/my-project/re-glissade/RUNS/run-2026-11-13g/k46-core411/core-pc.bin'
data = open(CORE, 'rb').read()
N = len(data) // 6
words = [int.from_bytes(data[i*6:(i+1)*6], 'big') for i in range(N)]

L, R = [], []
for i, w in enumerate(words):
    if (w >> 24) == 0o0100001:
        L.append(i)
    if (w & 0xffffff) == 0o0100001:
        R.append(i)
print('atx 1(1) L:', [oct(a) for a in L[:8]])
print('atx 1(1) R:', [oct(a) for a in R[:8]])

hits = []
for i, w in enumerate(words):
    if (w >> 24) & 0o77700000 == 0o70000000 and ((w >> 24) & 0o7777) != 0:
        hits.append((i, 'L', (w >> 24) & 0o7777))
    if (w & 0xffffff) & 0o77700000 == 0o70000000 and ((w & 0xffffff) & 0o7777) != 0:
        hits.append((i, 'R', (w & 0xffffff) & 0o7777))
print('atx X(16), X!=0:', [(oct(a), s, oct(x)) for a, s, x in hits[:20]])

# контекст вокруг первого кандидата
cand = None
for lst, side in ((L, 'L'), (R, 'R')):
    if lst:
        cand = lst[0]
if cand is not None:
    print(f'\n== Слова вокруг {oct(cand)} ==')
    for q in range(cand - 12, min(N, cand + 16)):
        print(f'{q:05o} {words[q]:016o}')
