#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-16: поиск МОНЫ-80 в физическом ядре по сигнатурам половинок:
- Э62 5747(М12) = 0o50625747 (вирт. 00421, финальный запрос)
- atx 10003(16) = 0o70010003 (вирт. 06210, билдер, 3 записи в 11043)
- rte/обработчик: ищем также page-окрестности."""
import sys

CORE = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/z/my-project/re-glissade/RUNS/run-2026-11-13g/k46-core411/core-pc.bin'
data = open(CORE, 'rb').read()
N = len(data) // 6
words = [int.from_bytes(data[i*6:(i+1)*6], 'big') for i in range(N)]

SIGS = {
    'Э62 5747(М12)': 0o50625747,
    'atx 10003(16)': 0o70010003,
}

for name, sig in SIGS.items():
    hits = []
    for i, w in enumerate(words):
        if (w >> 24) == sig:
            hits.append((i, 'L'))
        if (w & 0xffffff) == sig:
            hits.append((i, 'R'))
    print(f'{name} = {oct(sig)}: {len(hits)} попаданий:')
    for a, side in hits[:12]:
        print(f'   физ.{a:05o}{side}  (слово {words[a]:016o})')

# Контекст вокруг первого попадания atx 10003(16)
hits2 = [i for i, w in enumerate(words)
         if (w >> 24) == SIGS['atx 10003(16)'] or (w & 0xffffff) == SIGS['atx 10003(16)']]
if hits2:
    a = hits2[0]
    pg = a // 256
    print(f'\n== Контекст: физ.страница {pg:03o} ({pg*256:05o}-{pg*256+255:05o}) ==')
    lo = max(0, (a & ~0o377))
    for q in range(lo, min(N, lo + 256)):
        print(f'{q:05o} {words[q]:016o}')
