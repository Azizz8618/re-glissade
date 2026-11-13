#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-10 п.18.11(3): k46-прогон (LUN46 redirect) с дампом ядра.

BESM6_CORE_ON_PC=00411 - СТОП "КОНЕЦ ЗАДАЧИ" (штатный конец после
пустого листа ЛУН46). Дамп позволяет проверить IA/B (01121-01131) -
доходят ли слова карт из конверта до переменных задачи.

Использование: run_k46_core.py <workdir> [pc]
Ядро: <workdir>/core-pc.bin + core-uic.bin (форматы см. dispak/cu.c).
"""
import os
import subprocess
import sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
SEED = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13f/seed-k12.bin'
TOMS = ('2048', '2053', '2099', '2248')

CORE_ON_PC = sys.argv[2] if len(sys.argv) > 2 else '00411'
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
    'BESM6_LUN46_DRUM': '020',
    'BESM6_LUN46_TRACT': '05',
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
print(r.stderr[-600:] if r.stderr else '(stderr пуст)')
