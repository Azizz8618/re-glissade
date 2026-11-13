#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Проверка B(1..4)=[1121..1124] и IA(1..5)=[1125..1131] в дампах ядра k46.
# Формат дампa: core-pc.bin + core-uic.bin (см. dispak/cu.c).
# Формат float: код порядка = старшие 7 бит (смещение 64),
#   знак мантиссы = бит 8, мантисса = биты 9-48 (40 бит),
#   значение = m40/2^40 * 2^(код-64). Проверено: 0o4011463146314632 = 0.6.
import struct, sys

def get_real(word48):
    code = (word48 >> 41) & 0x7f
    mant = word48 & ((1 << 41) - 1)
    neg = bool(word48 & (1 << 40))          # бит 8 = знак мантиссы
    if neg:
        mant = (1 << 40) - (mant & ((1 << 40) - 1))
    v = (mant / float(1 << 40)) * (2.0 ** (code - 64))
    return -v if neg else v

def get_int(word48):
    # целое БЭСМ-6: доп. код 48 бит
    if word48 & (1 << 47):
        return word48 - (1 << 48)
    return word48

def load_core(path):
    # формат core-pc.bin: 16-бит слова, 65536 ячеек? проверим по размеру
    with open(path, 'rb') as f:
        data = f.read()
    return data

def word_at(data, addr):
    # 3 ushort на слово (48 бит) big-endian? формат cu.c: w_sh/w_sm/w_sl
    off = addr * 6
    a, b, c = struct.unpack_from('>HHH', data, off)
    return (a << 32) | (b << 16) | c

for core in sys.argv[1:]:
    data = load_core(core)
    n = len(data) // 6
    print("=== %s: %d слов (%d Кячеек)" % (core, n, n // 1024))
    # ищем максимум адреса из run.err не знаем; считаем 32768 ячеек стандарт
    base = 0o1121
    for i in range(0o1121, 0o1132):
        w = word_at(data, i)
        tag = {0o1121: 'B(1)', 0o1122: 'B(2)', 0o1123: 'B(3)', 0o1124: 'B(4)',
               0o1125: 'IA(1)?', 0o1126: 'IA(2)?', 0o1127: 'IA(3)?',
               0o1130: 'IA(4)?', 0o1131: 'IA(5)?'}[i]
        if w == 0:
            print("  [%o] %s: 0" % (i, tag))
        elif (w >> 41) & 0x7f >= 8 and (w & (1 << 40)) == 0:
            print("  [%o] %s: 0o%016o  float=%.6g" % (i, tag, w, get_real(w)))
        else:
            print("  [%o] %s: 0o%016o  int=%d" % (i, tag, w, get_int(w)))
