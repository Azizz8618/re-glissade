#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Эксперимент 3: конверт с МАСКАМИ в позициях 0o15-0o23 (аутентичная
раскладка член-листа 4023/0o554, ETAP1 п.11.10/12.10) и телом с 0o24.
Цель: проверить, меняет ли раскладка класс-слово W (сканер РЛС).
Варианты масок: k - однобитовые (таблица t6), z - нули, c - класс^K 6435.
"""
import subprocess
import sys

MK = '/home/z/my-project/re-glissade/TOOLS/mk_drum_seed_h.py'
WORK = '/tmp/w1'
DECK = '/home/z/my-project/re-glissade/RUNS/run-2026-11-13/TEST-READ-NL45.B6'
DISPAK = '/home/z/my-project/dispak/build/dispak/dispak'

# структура mk_drum_seed_h: HEADER 12 слов (0o0-0o11), маркер@0o12,
# [0o13]=0, тело с 0o14. Патчим: маски в 0o15-0o23, тело сдвигаем.
MASKS = [0o4000, 0o1000, 0o34000, 0o74000, 0o20000, 0o40000,
         0o100000, 0o200000, 0o404040404040]

def build_seed(out, mask_variant):
    """Читает mk_drum_seed_h как модуль, патчит build_zone, пишет seed."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('m', MK)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    orig_build = m.build_zone

    def build_zone_masked(deck_path, variant, cont=True):
        zone, conv, pos = orig_build(deck_path, variant, cont)
        if mask_variant == 'k':
            masks = MASKS
        elif mask_variant == 'z':
            masks = [0] * 9
        elif mask_variant == 'f':
            masks = [0o404040404040] * 9   # пробелы
        else:
            return zone, conv, pos
        for i, w in enumerate(masks):
            zone[0o15 + i] = w
            conv[0o15 + i] = m.CONV_CMD
        return zone, conv, pos

    m.build_zone = build_zone_masked
    cards = m.read_data_cards(DECK)
    recs = [m.build_zone(DECK, 'h', True), m.build_zone(DECK, 'h', False)]
    with open(out, 'wb') as f:
        for (zone, conv, pos) in recs:
            for w in zone:
                f.write(w.to_bytes(6, 'big'))
            for c in conv:
                f.write(bytes([c]))
    print(f'{mask_variant}: маски@0o15-0o23, тело до 0o{recs[0][2]:o}')

def run(seed, deck):
    env = {'BESM6_LUN45_DRUM': '020', 'BESM6_LUN45_TRACT': '04',
           'BESM6_DRUM_SEED': seed, 'BESM6_DRUM_SEED_DRUM': '020',
           'BESM6_WATCH': '3530', 'PATH': '/usr/bin:/bin'}
    r = subprocess.run([DISPAK, '--path=.', deck], cwd=WORK, env=env,
                       capture_output=True, text=True, errors='replace',
                       timeout=180)
    wvals = []
    for line in r.stderr.splitlines():
        if '76424R *75' in line:
            import re
            mm = re.search(r'AU=([0-9]+)', line)
            if mm:
                wvals.append(int(mm.group(1), 8))
    uw = []
    for v in wvals:
        if v not in uw:
            uw.append(v)
    e201 = 'ЕRRОR 201' in r.stdout
    ok = 'READ OK' in r.stdout
    rec = ''
    import re
    m2 = re.search(r'RЕСОRD(.*)', r.stdout)
    if m2:
        rec = m2.group(1)[:40]
    return uw, e201, ok, rec

if __name__ == '__main__':
    for mv in ('base', 'k', 'z', 'f'):
        seed = f'{WORK}/seed-mask-{mv}.bin'
        if mv == 'base':
            subprocess.run(['python3', MK, DECK, seed, 'h', '020', '04'],
                           capture_output=True)
        else:
            build_seed(seed, mv)
        uw, e201, ok, rec = run(seed, DECK)
        print(f'  W: {[f"{v:016o}" for v in uw[:4]]}  201={e201} OK={ok} {rec!r}')
