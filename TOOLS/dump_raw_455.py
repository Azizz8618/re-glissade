#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-6 п.17: декод ядра аутентичного (сырого) прогона.
Окна: [0410]-[0417] (характеристика MONCARD), [0502]-[0577]
(голова+таблица спула МОНА-80), [0600]-[0630] (КCOUNT*/MONCARD*).
Формат дампа: 65536 слов по 6 байт BE (dispak cu.c)."""
import sys, os

def load_core(path):
    core = []
    with open(path, 'rb') as f:
        data = f.read()
    for i in range(65536):
        w = int.from_bytes(data[i*6:(i+1)*6], 'big')
        core.append(w)
    return core

def iso_str(v):
    b = [(v >> s) & 0xFF for s in (40, 32, 24, 16, 8, 0)]
    out = ''
    for x in b:
        if x == 0o12:
            out += '~'
        elif 32 <= x < 127:
            out += chr(x)
        else:
            out += '.'
    return out

def dump(core, lo, hi, label):
    print(f'--- {label} [{lo:05o}..{hi:05o}] ---')
    for a in range(lo, hi + 1):
        v = core[a]
        print(f'[{a:05o}] {v:016o}  {iso_str(v)}')

if __name__ == '__main__':
    core = load_core(sys.argv[1])
    dump(core, 0o0502, 0o0577, 'МОНА-80 голова+таблица спула')
    dump(core, 0o0600, 0o0630, 'КCOUNT*/MONCARD*')
    dump(core, 0o0410, 0o0420, 'характеристика MONCARD/SIMFAIL')
