#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-15 п.18.16(1): имитация ПУСКа оператора после КОНЕЦ ЗАДАЧИ.
BESM6_EXIT_ADDR=00437 - *74 не останавливает машину, МОНА продолжает
с точки чтения след. записи потока (atx 0502, Э75 0004/Э70 0046/Э70 0061).
Вопрос: прочитав *end file и конец потока, займётся ли МОНА СПОЛ-выдачей
(печатью файла печати барабана 020 тракта 05 на АЦПУ)?
"""
import os, subprocess, sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
SEED = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13f/seed-k12.bin'
EXITADDR = sys.argv[1] if len(sys.argv) > 1 else '437'
work = sys.argv[2] if len(sys.argv) > 2 else '/tmp/k46restart'
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
    'BESM6_EXIT_ADDR': EXITADDR,
    'PATH': '/usr/bin:/bin',
})

r = subprocess.run([DISPAK, '--path=.', '--drum-dump=dd', DECK], cwd=work,
                   env=env, capture_output=True, text=True, errors='replace',
                   timeout=600)
with open(os.path.join(work, 'run.out'), 'w') as f:
    f.write(r.stdout)
with open(os.path.join(work, 'run.err'), 'w') as f:
    f.write(r.stderr)
print(r.stdout[-500:])
print('STDERR tail:', r.stderr[-400:] if r.stderr else '(пусто)')
print('files:', sorted(os.listdir(work)))
