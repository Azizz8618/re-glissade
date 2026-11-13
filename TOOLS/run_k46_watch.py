#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-11 п.18.13(4): k46-прогон с WATCH на записи в IA (01121).

BESM6_WATCH=01121, BESM6_WATCH_RW=1: печать каждой ЗАПИСИ по
исполнительному адресу 01121 (первое слово пары IA/B задачи) -
кто кладёт слова карт в переменные программы и когда.
Использование: run_k46_watch.py <workdir> <watch-адрес-восьм.>
"""
import os
import subprocess
import sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
SEED = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13f/seed-k12.bin'
TOMS = ('2048', '2053', '2099', '2248')

work, watch = sys.argv[1], sys.argv[2]
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
    'BESM6_WATCH': watch,
    'BESM6_WATCH_RW': '1',
    'BESM6_DD_DEBUG': '1',
    'PATH': '/usr/bin:/bin',
})

r = subprocess.run([DISPAK, '--path=.', DECK], cwd=work,
                   env=env, capture_output=True, text=True, errors='replace',
                   timeout=300)
with open(os.path.join(work, 'run.out'), 'w', encoding='utf-8') as f:
    f.write(r.stdout)
with open(os.path.join(work, 'watch.err'), 'w', encoding='utf-8') as f:
    f.write(r.stderr)
print(r.stderr[-500:] if r.stderr else '(stderr пуст)')
