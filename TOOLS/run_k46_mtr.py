#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-12 п.18.13(4): k46-прогон с MTR-окном на произвольный регион.

Сочетает конфигурацию k46 (LUN45+LUN46 redirect, сид k12) с MTR-окном.
Использование: run_k46_mtr.py <workdir> <MTR_LO-восьм.> <MTR_HI-восьм.> [N]
"""
import os
import subprocess
import sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
SEED = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13f/seed-k12.bin'
TOMS = ('2048', '2053', '2099', '2248')

work, mtr_lo, mtr_hi = sys.argv[1], sys.argv[2], sys.argv[3]
mtr_n = sys.argv[4] if len(sys.argv) > 4 else '30000'
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
    'BESM6_LUN46_DRUM': '020',
    'BESM6_LUN46_TRACT': '05',
    'BESM6_DRUM_SEED': SEED,
    'BESM6_DRUM_SEED_DRUM': '020',
    'BESM6_MTR_LO': mtr_lo,
    'BESM6_MTR_HI': mtr_hi,
    'BESM6_MTR_N': mtr_n,
    'BESM6_MTR_SKIP': '0',
    'BESM6_DD_DEBUG': '1',
    'PATH': '/usr/bin:/bin',
})

r = subprocess.run([DISPAK, '--path=.', DECK], cwd=work,
                   env=env, capture_output=True, text=True, errors='replace',
                   timeout=300)
with open(os.path.join(work, 'run.out'), 'w', encoding='utf-8') as f:
    f.write(r.stdout)
with open(os.path.join(work, 'mtr.txt'), 'w', encoding='utf-8') as f:
    f.write(r.stderr)
print(r.stderr[-400:] if r.stderr else '(stderr пуст)')
