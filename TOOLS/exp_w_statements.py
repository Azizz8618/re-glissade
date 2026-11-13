#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Эксперимент 2: зависимость W от ВИДА оператора READ (исходник Фортрана).
Меняем строку READ(5,100) в колоде, собираем seed-h, прогон, извлекаем W."""
import re
import subprocess

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
BASE_DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
MK_SEED = '/home/z/my-project/re-glissade/TOOLS/mk_drum_seed_h.py'
WORK = '/tmp/w1'

BASE_READ = '      READ(5,100) IA(1),IA(2),IA(3),IA(4),IA(5)'

def run_variant(name, read_line, fmt_line='  100 FORMAT(5I5)'):
    with open(BASE_DECK, encoding='utf-8') as f:
        txt = f.read()
    txt = txt.replace(BASE_READ, read_line)
    if fmt_line is not None:
        txt = txt.replace('  100 FORMAT(5I5)', fmt_line)
    deck = f'{WORK}/deck-s.b6'
    with open(deck, 'w', encoding='utf-8') as f:
        f.write(txt)
    seed = f'{WORK}/seed-s.bin'
    subprocess.run(['python3', MK_SEED, deck, seed, 'h', '020', '04'],
                   capture_output=True)
    env = {'BESM6_LUN45_DRUM': '020', 'BESM6_LUN45_TRACT': '04',
           'BESM6_DRUM_SEED': seed, 'BESM6_DRUM_SEED_DRUM': '020',
           'BESM6_WATCH': '3530', 'PATH': '/usr/bin:/bin'}
    r = subprocess.run([DISPAK, '--path=.', deck], cwd=WORK, env=env,
                       capture_output=True, text=True, errors='replace',
                       timeout=180)
    wvals = []
    for line in r.stderr.splitlines():
        if '76424R *75' in line:
            m = re.search(r'AU=([0-9]+)', line)
            if m:
                wvals.append(int(m.group(1), 8))
    # 201 в выводе (текст ГОСТ, ищем '201' рядом с ЕRRОR)
    has201 = 'ЕRRОR 201' in r.stdout or '201 DЕТЕСТЕD' in r.stdout
    hasok = 'READ OK' in r.stdout
    rec = re.search(r'RЕСОRD(.*)', r.stdout)
    rec = rec.group(1)[:30] if rec else ''
    # уникальные W
    uw = []
    for v in wvals:
        if v not in uw:
            uw.append(v)
    print(f'{name}')
    print(f'   W ({len(uw)} уник.): {[f"{v:016o}" for v in uw[:6]]}')
    print(f'   201={has201} READ_OK={hasok} запись: {rec!r}')

if __name__ == '__main__':
    run_variant('1. READ(5,100) IA(1)..IA(5)  [базовый]', BASE_READ)
    run_variant('2. READ(5,100) IA(1)          [1 элемент]', '      READ(5,100) IA(1)')
    run_variant('3. READ(5,100)                [без списка]', '      READ(5,100)')
    run_variant('4. READ(5) IA(1)              [без формата]', '      READ(5) IA(1)')
    run_variant('5. READ(5,100,END=900) IA(1)  [с END=]', '      READ(5,100,END=900) IA(1)\n 900 CONTINUE')
