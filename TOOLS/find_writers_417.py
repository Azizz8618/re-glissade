#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поиск команд, пишущих в ячейку [0417], в бинарных образах (ядро, зоны дисков).
Декодирование = макросы dispak/defs.h (Lreg/Lstruct/Lop/Laddr, то же для right).
Пишущие опкоды (optab.c): atx 000, stx 001, amx 007, apx 020, aux 021,
acx 022, anx 023; структурные: МТМ (запись модификатора) и др. по таблице.
"""
import sys

WRITE_OPS = {0o000: 'atx', 0o001: 'stx', 0o007: 'amx', 0o020: 'apx',
             0o021: 'aux', 0o022: 'acx', 0o023: 'anx'}

# структурные (0o100+): МТМ = запись модификатора в память, СТМ и пр.
STRUCT_WRITE = {0o150: 'mtm', 0o140: 'мтм?', 0o110: 'stx-struct'}

def decode(ins24):
    """24-битная команда -> (reg, struct, exp, op, addr)."""
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
    return reg, struct, exp, op, addr

def scan_words(name, words):
    """words: iterable 48-битных ячеек. Печатает команды записи в 0417."""
    for wi, v in enumerate(words):
        for half, ins24 in (('L', (v >> 24) & 0xFFFFFF),
                            ('R', v & 0xFFFFFF)):
            reg, struct, exp, op, addr = decode(ins24)
            nm = WRITE_OPS.get(op)
            if not nm and struct:
                nm = STRUCT_WRITE.get(op)
            if nm and (addr & 0o77777) == 0o417:
                print(f'{name} слово {wi:6d} {half} {nm:4s} '
                      f'{addr:04o}({reg:o}) struct={struct} raw={ins24:07o}')

def scan_binary(name, data, word_size=6, offset=0, count=None):
    n = len(data) // word_size
    if count:
        n = min(n, count)
    for i in range(n):
        v = int.from_bytes(data[offset + i*word_size: offset + i*word_size + 6], 'big')
        yield v

if __name__ == '__main__':
    for path in sys.argv[1:]:
        data = open(path, 'rb').read()
        if path.endswith('.bin') or path.isdigit():
            scan_binary(path, data) and None
            scan_words(path, scan_binary(path, data))
        else:
            # зона: 64Б конволюции + 6144Б данных
            zs = 64 + 1024 * 6
            nz = len(data) // zs
            for z in range(nz):
                off = z * zs + 64
                scan_words(f'{path} з0o{z:03o}',
                           scan_binary(f'{path} з0o{z:03o}', data, offset=off,
                                       count=1024))
