#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core-pc.bin: окрестности находок заполнителя, таблица классов 6360-6440,
побайтовая структура буфера 76000, поиск КCOUNT*. Сессия 13.11.26."""
CORE = "/home/z/my-project/work/re-glissade/RUNS/run-2026-11-12/core-pc.bin"
data = open(CORE, "rb").read()
N = len(data) // 6
words = [int.from_bytes(data[i*6:(i+1)*6], "big") for i in range(N)]

def O(w): return "0o" + format(w, "016o")

def iso(w):
    """ISO-8бит посимвольно: '~'=0x0A, прочие управляющие как ..NN"""
    out = []
    for shift in (40, 32, 24, 16, 8, 0):
        b = (w >> shift) & 0xFF
        if b == 0x0A: out.append("~")
        elif 0x20 <= b < 0x7F: out.append(chr(b))
        else: out.append("[%02X]" % b)
    return "".join(out)

def gost(w):
    tbl = {0o12: 'EOR', 0o13: 'CR', 0o11: 'TAB', 0o15: 'LF', 0o34: ' '}
    out = []
    for shift in (42, 36, 30, 24, 18, 12, 6, 0):
        b = (w >> shift) & 0o77
        if b == 0: out.append('.')
        elif b in tbl: out.append(tbl[b])
        else: out.append("%02o" % b)
    return "|".join(out)

def dump(lo, hi, title):
    print(f"\n== {title} ==")
    for a in range(lo, hi):
        w = words[a]
        print(f"  [{a:05o}] = {O(w)}")
        print(f"          iso='{iso(w)}'")

# 1. Заполнитель+EOR: окрестности находок
dump(0o75435, 0o75452, "ОКРЕСТНОСТЬ 75442 (стек RWBT)")
dump(0o57125, 0o57145, "ОКРЕСТНОСТЬ 57135 (runtime Фортрана)")
dump(0o30500 - 6, 0o30512, "ОКРЕСТНОСТЬ 30500")
dump(0o00616, 0o00630, "МОНИТОР-резидент: таблица заполнителей 0o607-0o624")

# 2. Таблица классов 6360-6440 (дескриптор формата записи!)
print("\n== ТАБЛИЦА КЛАССОВ 6360-6440 ==")
for a in range(0o6360, 0o6440):
    w = words[a]
    print(f"  [{a:05o}] = {O(w)}  gost='{gost(w)}'")

# 3. Буфер 76000-76250 побайтно (структура записей МОНИТОРА)
print("\n== БУФЕР 76000-76250, ISO-посимвольно ==")
for a in range(0o76000, 0o76250):
    w = words[a]
    lb = w & 0o77
    mark = ""
    if lb in (0o12, 0o13): mark = f"  <== конец байта {0o12 if lb==0o12 else 0o13}"
    print(f"  [{a:05o}] = {O(w)}  iso='{iso(w)}'{mark}")

# 4. Поиск КCOUNT*: 4 слова, [x+3]>>20 == 0o45 (ЛУН 45)
print("\n== ПОИСК КCOUNT* ([x+3]>>20 == 0o45) ==")
for x in range(N - 3):
    if (words[x+3] >> 20) == 0o45 and words[x+3] != 0:
        print(f"  кандидат x={x:05o}: [{O(words[x])}] [{O(words[x+1])}] "
              f"[{O(words[x+2])}] [{O(words[x+3])}]")
