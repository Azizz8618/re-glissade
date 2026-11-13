#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Реконструкция текста печати задачи Tstread из dd.m20 (барабан 020, зона 5).
# Формат файла печати МОНЫ-80: ISO-8бит, байт 0o200+N = N пробелов (RLE),
# EOR 0o12 инлайн, запись = строка печати.
import sys

words = {}
for line in open('/home/z/my-project/re-glissade/RUNS/run-2026-11-13g/k46-print/dd.m20',
                 encoding='utf-8', errors='replace'):
    line = line.strip()
    if not line or line.startswith('в '):
        continue
    parts = line.split(';')
    if len(parts) < 3:
        continue
    try:
        addr = int(parts[2].strip(), 8)
    except ValueError:
        continue
    octs = [o for o in ''.join(ch for ch in parts[1] if ch in '01234567 ').split()]
    w = 0
    for o in octs[:4]:
        w = (w << 12) | int(o, 8)
    words[addr] = w

zone5 = [(a, words[a]) for a in sorted(words) if 0o12000 <= a < 0o14000 and words[a]]
# слова зоны 5 -> байты по 6 на слово (старший первым)
data = bytearray()
for a, w in zone5:
    data += bytes((w >> s) & 0xFF for s in (40, 32, 24, 16, 8, 0))

# RLE-развёртка и разбор на строки по EOR 0o12
out, cur = [], bytearray()
for b in data:
    if b >= 0o200:
        cur += b' ' * (b - 0o200)
    elif b == 0o12:
        out.append(bytes(cur)); cur = bytearray()
    elif b == 0:
        if cur: out.append(bytes(cur)); cur = bytearray()
    else:
        cur.append(b)
if cur:
    out.append(bytes(cur))

with open('/home/z/my-project/re-glissade/RUNS/run-2026-11-13g/k46-print/printfile.txt', 'w') as f:
    f.write("Файл печати задачи Tstread (барабан 020 зона 5, ISO+RLE, EOR 0o12)\n")
    f.write("Источник: k46-print/dd.m20 (А2 13.11-14, п.18.15(2))\n\n")
    for i, line in enumerate(out, 1):
        try:
            t = line.decode('ascii')
        except UnicodeDecodeError:
            t = repr(bytes(line))
        f.write("%3d |%s|\n" % (i, t))
        print("%3d |%s|" % (i, t))
