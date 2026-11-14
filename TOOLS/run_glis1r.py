#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-17 п.А3(1): прогон ГЛИССАДА (GLIS1R-NL, 6 модулей GLNUMR)
на живом READ-конвейере: конфиг k46 (LUN45/46 redirect + seed-k12
с теми же картами данных) + BESM6_EXIT_ADDR для спул-выдачи.

Использование: run_glis1r.py <workdir> [deck] [exitaddr] [mtr_lo mtr_hi n]
"""
import os
import shutil
import subprocess
import sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
SEED = os.environ.get('GLIS1R_SEED',
                      '/home/z/my-project/re-glissade/RUNS/run-2026-11-13f/seed-k12.bin')
TOMS = ('2048', '2053', '2099', '2248')

work = sys.argv[1]
deck = sys.argv[2] if len(sys.argv) > 2 else \
    '/home/z/my-project/re-glissade/RUNS/run-2026-11-14/GLIS1R-NL.B6'
exitaddr = sys.argv[3] if len(sys.argv) > 3 else '437'
os.makedirs(work, exist_ok=True)
for t in TOMS:
    dst = os.path.join(work, t)
    if not os.path.exists(dst):
        try:
            os.symlink(f'/home/z/my-project/dispak/build/dispak/{t}', dst)
        except OSError:
            shutil.copy(f'/home/z/my-project/dispak/build/dispak/{t}', dst)

env = dict(os.environ)
env.update({
    'BESM6_LUN45_DRUM': '020',
    'BESM6_LUN45_TRACT': '04',
    'BESM6_LUN45_EXECUTE': '414',
    'BESM6_LUN46_DRUM': '020',
    'BESM6_LUN46_TRACT': '05',
    'BESM6_NTV_TRACT': '06',
    'BESM6_DECK': deck,        # v13: колода для k12-конверта (native-путь)
    'BESM6_DD_DEBUG': '1',
    'BESM6_EXIT_ADDR': exitaddr,
    'PATH': '/usr/bin:/bin',
})
# А2 13.11-18 п.18.18(1): натуральный путь - конверт-вид родной зоны
# из УИР (GLIS1R_NATIVE=1): redirect без форсирования тракта, сид НЕ
# подсаживать, данные берутся 1:1 из нативной зоны 20/04.
if os.environ.get('GLIS1R_NATIVE'):
    env['BESM6_LUN45_NATIVE'] = '1'
if SEED and SEED != 'none':
    env['BESM6_DRUM_SEED'] = SEED
    env['BESM6_DRUM_SEED_DRUM'] = '020'
tail = os.environ.get('GLIS1R_LUN_TAIL')
if tail:
    env['BESM6_LUN_TAIL'] = tail
if len(sys.argv) > 6:
    env.update({
        'BESM6_MTR_LO': sys.argv[4],
        'BESM6_MTR_HI': sys.argv[5],
        'BESM6_MTR_N': sys.argv[6],
        'BESM6_MTR_SKIP': '0',
    })

r = subprocess.run([DISPAK, '--path=.', '--drum-dump=dd', deck], cwd=work,
                   env=env, capture_output=True, text=True, errors='replace',
                   timeout=1200)
with open(os.path.join(work, 'run.out'), 'w', encoding='utf-8') as f:
    f.write(r.stdout)
with open(os.path.join(work, 'run.err'), 'w', encoding='utf-8') as f:
    f.write(r.stderr)
if os.path.exists(os.path.join(work, 'dd.m20')):
    with open(os.path.join(work, 'printfile.txt'), 'w', encoding='utf-8') as f:
        subprocess.run([sys.executable,
                        '/home/z/my-project/re-glissade/TOOLS/decode_print_glis1r.py',
                        os.path.join(work, 'dd.m20'), '4', '7'],
                       stdout=f, stderr=subprocess.DEVNULL)
for marker in ('ОШ', 'ОТСУТСТВ', 'ИСПОРЧЕН', 'ГЛИССАДА', 'СКО', 'ОЦЕНКА',
               'READ OK', 'КОНЕЦ ЗАДАЧИ', 'T=', 'OCENKA'):
    n = r.stdout.count(marker)
    if n:
        print(f'{marker}: {n}')
print('--- stdout tail ---')
print(r.stdout[-800:])
