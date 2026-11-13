#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-8 п.18.8(1): k1-прогон с дампом ядра в момент смерти читателя.

BESM6_CORE_ON_PC=04050 - pc первой проверки после xta [76000+М4]
(чтение 25-го слова тела [76044] при М4=0o44). Требует BESM6_DD_DEBUG=1.

Использование: run_k1_core.py <workdir>
Ядро: <workdir>/core-pc.bin + core-uic.bin (форматы см. dispak/cu.c).
"""
import os
import subprocess
import sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
SEED = sys.argv[3] if len(sys.argv) > 3 else \
    '/home/z/my-project/re-glissade/RUNS/run-2026-11-13e/seed-k1.bin'
TOMS = ('2048', '2053', '2099', '2248')

CORE_ON_PC = sys.argv[2] if len(sys.argv) > 2 else '04050'

work = sys.argv[1]
os.makedirs(work, exist_ok=True)
for t in TOMS:
    dst = os.path.join(work, t)
    if not os.path.exists(dst):
        os.symlink(f'/home/z/my-project/dispak/build/dispak/{t}', dst)

env = dict(os.environ)
env.update({
    'BESM6_LUN45_DRUM': '020',
    'BESM6_LUN45_TRACT': '04',
    'BESM6_LUN45_EXECUTE': '414',
    'BESM6_DRUM_SEED': SEED,
    'BESM6_DRUM_SEED_DRUM': '020',
    'BESM6_CORE_ON_PC': CORE_ON_PC,
    'BESM6_DD_DEBUG': '1',
    'PATH': '/usr/bin:/bin',
})

r = subprocess.run([DISPAK, '--path=.', DECK], cwd=work,
                   env=env, capture_output=True, text=True, errors='replace',
                   timeout=300)
with open(os.path.join(work, 'run.out'), 'w', encoding='utf-8') as f:
    f.write(r.stdout)
with open(os.path.join(work, 'run.err'), 'w', encoding='utf-8') as f:
    f.write(r.stderr)
for marker in ('CORE DUMPED', 'ИСПОРЧЕН', 'POINT', 'READ OK'):
    hit = marker in r.stderr or marker in r.stdout
    print(f'{marker}: {"ДА" if hit else "нет"}')
print('файлы:',
      [x for x in sorted(os.listdir(work)) if x.startswith('core-')])
