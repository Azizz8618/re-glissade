#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-16 п.18.16(2): прогон с ПУСКом (BESM6_EXIT_ADDR=412),
WATCH-адресом записи и дампом ядра на pc=00422 (возврат из Э62,
момент «Пока рано»). Дамп: core-pc.bin (физ.) + core-uic.bin
(кэш команд по ВИРТУАЛЬНЫМ адресам - см. disasm_uic.py).

Использование: run_k46_core2.py <workdir> <watch-адрес-восьм.> [pc]
"""
import os
import subprocess
import sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
SEED = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13f/seed-k12.bin'

work = sys.argv[1]
watch = sys.argv[2]
pc = sys.argv[3] if len(sys.argv) > 3 else '00422'
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
    'BESM6_EXIT_ADDR': '412',
    'BESM6_WATCH': watch,
    'BESM6_WATCH_RW': '1',
    'BESM6_CORE_ON_PC': pc,
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
tail = r.stderr[-300:] if r.stderr else '(stderr пуст)'
print(tail)
print('files:', sorted(os.listdir(work)))
