#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-14 п.18.15(2): k46-прогон с --drum-dump: файл печати задачи
(ЛУН46 WR -> барабан 020 зона 0005) должен содержать вывод WRITE(6):
"IA =    3    1    0    5    1", "B =  2400.00   7351.00 ..." , "READ OK".
"""
import os, subprocess, sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
SEED = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13f/seed-k12.bin'
work = sys.argv[1] if len(sys.argv) > 1 else '/tmp/k46print'
os.makedirs(work, exist_ok=True)
for t in ('2048', '2053', '2099', '2248'):
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
    'BESM6_DD_DEBUG': '1',
    'PATH': '/usr/bin:/bin',
})

r = subprocess.run([DISPAK, '--path=.', '--drum-dump=dd', DECK], cwd=work,
                   env=env, capture_output=True, text=True, errors='replace',
                   timeout=300)
with open(os.path.join(work, 'run.out'), 'w') as f:
    f.write(r.stdout)
with open(os.path.join(work, 'run.err'), 'w') as f:
    f.write(r.stderr)
print(r.stdout[-400:])
print('STDERR tail:', r.stderr[-300:] if r.stderr else '(пусто)')
print('files:', sorted(os.listdir(work)))
