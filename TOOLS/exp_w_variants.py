#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Эксперимент А2 (п.14): как содержание записи влияет на класс-слово W.
Для каждого варианта карты данных: собирает колоду, seed-h-раскладку,
прогон, извлекает W (последняя запись Э75 в [03530] перед чтением 01546R).
"""
import re
import subprocess
import sys

DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'
BASE_DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
MK_SEED = '/home/z/my-project/re-glissade/TOOLS/mk_drum_seed_h.py'
WORK = '/tmp/w1'

def make_deck(out, repl):
    with open(BASE_DECK, encoding='utf-8') as f:
        lines = f.readlines()
    done = False
    for i, ln in enumerate(lines):
        if not done and ln.strip() == '*execute':
            done = True
            continue
        if done:
            if ln.strip().lower().startswith('*end file'):
                break
            if repl and not repl.pop(0) is None:
                lines[i] = repl.pop(0) if False else ''
    # проще: перечитаем и подменим по индексам
    return lines

def variant_deck(out, card1, card2):
    with open(BASE_DECK, encoding='utf-8') as f:
        txt = f.read()
    txt = txt.replace('    3    1    0    5    1', card1)
    txt = txt.replace('   2400.   7351.     1.5     .60', card2)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(txt)

def run(deck, seed, tag):
    env = {
        'BESM6_LUN45_DRUM': '020', 'BESM6_LUN45_TRACT': '04',
        'BESM6_DRUM_SEED': seed, 'BESM6_DRUM_SEED_DRUM': '020',
        'BESM6_WATCH': '3530', 'PATH': '/usr/bin:/bin',
    }
    r = subprocess.run([DISPAK, '--path=.', deck], cwd=WORK, env=env,
                       capture_output=True, text=True, errors='replace',
                       timeout=120)
    err = r.stderr
    wvals = []
    seen_xta = False
    for line in err.splitlines():
        if '01546R xta' in line:
            seen_xta = True
        if '76424R *75' in line:
            m = re.search(r'AU=([0-9]+)', line)
            if m:
                wvals.append((int(m.group(1), 8), seen_xta))
    ok = 'READ OK' in r.stdout
    err201 = 'I/O-ERROR 201' in r.stdout
    return wvals, ok, err201

def main():
    variants = [
        ('базовый  5I5', '    3    1    0    5    1', '   2400.   7351.     1.5     .60'),
        ('буквы    5I5', 'ABCDE    1    0    5    1', '   2400.   7351.     1.5     .60'),
        ('пробелы  5I5', ' ' * 20, '   2400.   7351.     1.5     .60'),
        ('звёздочка    ', '  *  ABCDEFGH', '   2400.   7351.     1.5     .60'),
        ('точки/запятая', ' 1,2.3  4 5 6', '   2400.   7351.     1.5     .60'),
    ]
    for name, c1, c2 in variants:
        deck = f'{WORK}/deck-x.b6'
        variant_deck(deck, c1, c2)
        seed = f'{WORK}/seed-x.bin'
        subprocess.run(['python3', MK_SEED, deck, seed, 'h', '020', '04'],
                       capture_output=True)
        wvals, ok, err201 = run(deck, seed, name)
        wlist = [f'{v:016o}{"(после xta)" if sx else ""}' for v, sx in wvals[-3:]]
        print(f'{name}: READ_OK={ok} 201={err201} W-записи: {wlist}')

if __name__ == '__main__':
    main()
