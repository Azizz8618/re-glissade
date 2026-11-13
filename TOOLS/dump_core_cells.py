#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разбор core-pc.bin (дамп ядра 64К в момент контроля IOCONT*).
Печатает окна ячеек в восьмеричном и как ISO/ГОСТ-текст."""
import sys

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
            out += '~EOR~'
        elif 32 <= x < 127:
            out += chr(x)
        else:
            out += f'<{x:03o}>'
    return out

def dump(core, lo, hi, label):
    print(f'--- {label} [{lo:05o}..{hi:05o}] ---')
    for a in range(lo, hi + 1):
        v = core[a]
        print(f'[{a:05o}] {v:016o}  {iso_str(v)}')

if __name__ == '__main__':
    core = load_core(sys.argv[1])
    what = sys.argv[2] if len(sys.argv) > 2 else 'all'
    if what in ('all', 'win'):
        dump(core, 0o64470, 0o64540, 'окно спула/буфер')
    if what in ('all', 'stage'):
        dump(core, 0o2030, 0o2042, 'зона копирования IOCONT')
    if what in ('all', 'w'):
        dump(core, 0o2400, 0o2405, 'W=[02401]')
        dump(core, 0o3525, 0o3535, '[03530] зона')
        print(f"[0417] = {core[0o417]:016o}")
    if what in ('all', 'list'):
        dump(core, 0o76000, 0o76050, 'лист МОНИТОРА (буфер 76000)')
