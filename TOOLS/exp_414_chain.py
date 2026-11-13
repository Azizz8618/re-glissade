#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Эксперимент 14.8(1)-A: ротация РЛС и ячейки 0o414-0o417.
Проверка: (а) в форматном прогоне [0416] получает вес 0o20 (следующая
стадия за 0o64), а [0417] НЕ пишется; (б) в безформатном прогоне
(READ(5) IA(1), W бит 14=1) ротация доходит до 0417.
Извлекаем только РЕАЛЬНЫЕ обращения (исключая utm/vjm/vlm/vzm/v1m/
uza/u1a/uj/mtj/vtm - ложные EA по диспаковской формуле операнда)."""
import re
import subprocess

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
BASE_DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
MK_SEED = '/home/z/my-project/re-glissade/TOOLS/mk_drum_seed_h.py'
WORK = '/tmp/w1'

BASE_READ = '      READ(5,100) IA(1),IA(2),IA(3),IA(4),IA(5)'

FALSE_OPS = ('utm', 'vjm', 'vlm', 'vzm', 'v1m', 'uza', 'u1a', ' uj ',
             'mtj', 'vtm', 'sti', 'xts 77777')


def run(name, watch, deck):
    seed = f'{WORK}/seed-exp.bin'
    subprocess.run(['python3', MK_SEED, deck, seed, 'h', '020', '04'],
                   capture_output=True)
    env = {'BESM6_LUN45_DRUM': '020', 'BESM6_LUN45_TRACT': '04',
           'BESM6_DRUM_SEED': seed, 'BESM6_DRUM_SEED_DRUM': '020',
           'BESM6_WATCH': watch, 'PATH': '/usr/bin:/bin'}
    r = subprocess.run([DISPAK, '--path=.', deck], cwd=WORK, env=env,
                       capture_output=True, text=True, errors='replace',
                       timeout=180)
    real = []
    for line in r.stderr.splitlines():
        if not line.startswith('WATCH'):
            continue
        if any(op in line[13:26] for op in FALSE_OPS):
            continue
        real.append(line)
    # события ротации 64424 (СТХ/Э75) с М5-значением
    rot = [ln for ln in real if '64424' in ln]
    has201 = 'ЕRRОR 201' in r.stdout
    hasok = 'READ OK' in r.stdout
    rec = re.search(r'RЕСОRD(.*)', r.stdout)
    rec = rec.group(1)[:30] if rec else ''
    print(f'== {name}  WATCH={watch}')
    print(f'   реальных обращений: {len(real)}, из них ротация 64424: {len(rot)}')
    for ln in real[:12]:
        print('   ' + ln[:110])
    if rot:
        print('   --- ротация:')
        for ln in rot[:8]:
            m = re.search(r'\) EA=(\d+) (WR|RD) AU=(\d+)', ln)
            if m:
                print(f'     EA={int(m.group(1),8):05o} {m.group(2)} '
                      f'AU={int(m.group(3),8):016o}')
    print(f'   201={has201} READ_OK={hasok} запись: {rec!r}')
    return real


if __name__ == '__main__':
    # (а) базовый форматный прогон
    run('ФОРМАТНЫЙ READ(5,100) IA(1..5)', '0416', BASE_DECK)
    run('ФОРМАТНЫЙ READ(5,100) IA(1..5)', '0417', BASE_DECK)
    # (б) безформатный маршрут
    with open(BASE_DECK, encoding='utf-8') as f:
        txt = f.read()
    unf = txt.replace(BASE_READ, '      READ(5) IA(1)')
    deck = f'{WORK}/deck-unf.b6'
    with open(deck, 'w', encoding='utf-8') as f:
        f.write(unf)
    run('БЕЗФОРМАТНЫЙ READ(5) IA(1)', '0416', deck)
    run('БЕЗФОРМАТНЫЙ READ(5) IA(1)', '0417', deck)
