#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-8: k-прогон с MTR-трассой читателя (окно 03500-03700).

Использование: run_k_mtr.py <workdir> <seed.bin> [mtr-n]
Снимает stderr (MTR) в <workdir>/mtr.txt.
"""
import os
import subprocess
import sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
TOMS = ('2048', '2053', '2099', '2248')

work, seed = sys.argv[1], sys.argv[2]
mtr_n = sys.argv[3] if len(sys.argv) > 3 else '0'   # 0 = без трассы
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
    'BESM6_DRUM_SEED': seed,
    'BESM6_DRUM_SEED_DRUM': '020',
    'PATH': '/usr/bin:/bin',
})
if mtr_n != '0':
    env.update({
        'BESM6_MTR_LO': os.environ.get('MTR_LO','03500'),
        'BESM6_MTR_HI': os.environ.get('MTR_HI','03700'),
        'BESM6_MTR_N': mtr_n,
        'BESM6_MTR_SKIP': '0',
        'BESM6_DD_DEBUG': '1',
    })

r = subprocess.run([DISPAK, '--path=.', DECK], cwd=work,
                   env=env, capture_output=True, text=True, errors='replace',
                   timeout=600)
with open(os.path.join(work, 'mtr.txt'), 'w', encoding='utf-8') as f:
    f.write(r.stderr)
with open(os.path.join(work, 'run.out'), 'w', encoding='utf-8') as f:
    f.write(r.stdout)
print(f'MTR строк: {r.stderr.count(chr(10))}')
for marker in ('ИСПОРЧЕН', 'POINT', 'READ OK'):
    print(f'{marker}: {"ДА" if marker in r.stdout else "нет"}')
