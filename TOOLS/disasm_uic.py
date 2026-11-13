#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Дизассемблер дампа кэша команд (core-uic.bin, патч dispak 13.11).

Формат: 65536 слов по 6 байт; слово = две 24-бит записи инструкции,
каждая упакована как reg<<20 | opcode<<12 | addr (dispak/cu.c, Шаги 6-7).
В отличие от disasm_core.py (декодирование сырой памяти М-формата) здесь
опкод уже объединён (структурные 0o100+), адрес 12 бит без эксп-бита.

Использование: disasm_uic.py <файл-uic.bin> <начало-восьм.> <конец-восьм.>
"""
import sys

EXTNAMES = {
    0o00: 'atx', 0o01: 'stx', 0o02: 'mod', 0o03: 'xts',
    0o04: 'a+x', 0o05: 'a-x', 0o06: 'x-a', 0o07: 'amx',
    0o10: 'xta', 0o11: 'aax', 0o12: 'aex', 0o13: 'arx', 0o14: 'avx',
    0o15: 'aox', 0o16: 'a/x', 0o17: 'a*x', 0o20: 'apx', 0o21: 'aux',
    0o22: 'acx', 0o23: 'anx', 0o24: 'e+x', 0o25: 'e-x', 0o26: 'asx',
    0o27: 'xtr', 0o30: 'rte', 0o31: 'yta', 0o32: 'ext', 0o33: 'ext',
    0o34: 'e+n', 0o35: 'e-n', 0o36: 'asn', 0o37: 'ntr', 0o40: 'ati',
    0o41: 'sti', 0o42: 'ita', 0o43: 'its', 0o44: 'mtj', 0o45: 'm+j',
    0o46: 'x46', 0o47: '*47',
}
for n in range(0o50, 0o100):
    EXTNAMES[n] = 'Э%02o' % n
EXTNAMES2 = {
    0o100: '*20', 0o101: '*21', 0o102: 'utc', 0o103: 'wtc',
    0o104: 'vtm', 0o105: 'utm', 0o106: 'uza', 0o107: 'u1a',
    0o110: 'uj', 0o111: 'vjm', 0o112: 'iret', 0o113: 'stop',
    0o114: 'vzm', 0o115: 'v1m', 0o116: 'X36', 0o117: 'vlm',
}


def decode(c24):
    reg = (c24 >> 20) & 0o17
    op = (c24 >> 12) & 0o377
    addr = c24 & 0o7777
    if op >= 0o100:
        name = EXTNAMES2.get(op, 'Э%o' % (op - 0o100))
    else:
        name = EXTNAMES.get(op, '??%02o' % op)
    return '%-5s %04o(%o)' % (name, addr, reg)


def main():
    path, a0, a1 = sys.argv[1], int(sys.argv[2], 8), int(sys.argv[3], 8)
    with open(path, 'rb') as f:
        data = f.read()
    for a in range(a0, a1 + 1):
        off = a * 6
        b = data[off:off + 6]
        if len(b) < 6:
            break
        c0 = (b[0] << 16) | (b[1] << 8) | b[2]
        c1 = (b[3] << 16) | (b[4] << 8) | b[5]
        if c0 == 0 and c1 == 0:
            print('%05o  ---          | ---          ; не исполнялось' % a)
        else:
            print('%05o  %-12s | %-12s ; %08o %08o' % (
                a, decode(c0), decode(c1), c0, c1))


if __name__ == '__main__':
    main()
