#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поиск ВСЕХ обращений (любые опкоды) к ячейкам 0o414-0o417 в
образе памяти (core-pc.bin) и в кэше команд (core-uic.bin).
Плюс поиск команд с малыми адресами через базовые регистры:
печатает контекст для анализа косвенных записей.
Декодирование = макросы dispak/defs.h."""
import sys

NAMES = {
    0o000: 'atx', 0o001: 'stx', 0o002: 'mod', 0o003: 'xts',
    0o004: 'a+x', 0o005: 'a-x', 0o006: 'x-a', 0o007: 'amx',
    0o010: 'xta', 0o011: 'aax', 0o012: 'aex', 0o013: 'arx', 0o014: 'avx',
    0o015: 'aox', 0o016: 'a/x', 0o017: 'a*x', 0o020: 'apx', 0o021: 'aux',
    0o022: 'acx', 0o023: 'anx', 0o024: 'e+x', 0o025: 'e-x', 0o026: 'asx',
    0o027: 'xtr', 0o030: 'rte', 0o031: 'yta', 0o032: 'ext',
    0o036: 'asn', 0o037: 'ntr', 0o040: 'ati', 0o041: 'sti', 0o042: 'ita',
    0o043: 'its', 0o044: 'mtj', 0o045: 'm+j',
}
for n in range(0o50, 0o100):
    NAMES[n] = 'Э%02o' % n
NAMES2 = {
    0o102: 'utc', 0o103: 'wtc', 0o104: 'vtm', 0o105: 'utm', 0o106: 'uza',
    0o107: 'u1a', 0o110: 'uj', 0o111: 'vjm', 0o112: 'iret', 0o113: 'stop',
    0o114: 'vzm', 0o115: 'v1m', 0o116: 'X36', 0o117: 'vlm',
}

def decode(ins24):
    b0 = (ins24 >> 16) & 0xFF
    b1 = (ins24 >> 8) & 0xFF
    b2 = ins24 & 0xFF
    reg = b0 >> 4
    struct = b0 & 8
    exp = b0 & 4
    if struct:
        op = ((((b1 >> 7) | (b0 << 1)) & 0xF) | 0o100)
        addr = ((b1 << 8) | b2) & 0o77777
    else:
        op = (((b1 >> 4) | (b0 << 4)) & 0o77)
        addr = ((b1 << 8) | b2) & 0o7777
        if exp:
            addr |= 0o70000
    return reg, struct, op, addr

def name(op):
    return NAMES.get(op) or NAMES2.get(op) or '??%02o' % op

def load_cells(path):
    data = open(path, 'rb').read()
    return [int.from_bytes(data[i*6:(i+1)*6], 'big')
            for i in range(len(data)//6)]

def main():
    path = sys.argv[1]
    lo = int(sys.argv[2], 8) if len(sys.argv) > 2 else 0o414
    hi = int(sys.argv[3], 8) if len(sys.argv) > 3 else 0o417
    cells = load_cells(path)
    n = len(cells)
    print(f'# {path}: {n} ячеек (0o{len(cells):o}), цели {lo:04o}-{hi:04o}')
    for a, v in enumerate(cells):
        for hw, ins24 in (('L', (v >> 24) & 0xFFFFFF),
                          ('R', v & 0xFFFFFF)):
            reg, struct, op, addr = decode(ins24)
            if lo <= addr <= hi:
                print(f'{a:05o}{hw} {name(op):5s} {addr:04o}({reg:o}) '
                      f'raw={ins24:07o}')

if __name__ == '__main__':
    main()
