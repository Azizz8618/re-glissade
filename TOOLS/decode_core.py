#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Декодирование core-pc.bin (6 байт/слово BE): MONCARD*, буфер 76000,
supervisor-ячейки [43Б]/[57Б]/[60Б]/[61Б]/[70Б], поиск слова-заполнителя
0o1002004010020012 и его версий. Сессия 13.11.26, шаг: декод MONCARD*."""
import sys

CORE = "/home/z/my-project/work/re-glissade/RUNS/run-2026-11-12/core-pc.bin"
# читаем BE (старший байт первым), 6 байт/слово
data = open(CORE, "rb").read()
N = len(data) // 6
words = [int.from_bytes(data[i*6:(i+1)*6], "big") for i in range(N)]
assert N == 32768, N

def O(w):
    return "0o" + format(w, "016o")

def iso_text(w):
    """ISO-8бит: 6 символов/слово, EOR-байты (0x0A) как '~'."""
    out = []
    for shift in (40, 32, 24, 16, 8, 0):
        b = (w >> shift) & 0xFF
        out.append("~" if b == 0x0A else (chr(b) if 0x20 <= b < 0x7F else "."))
    return "".join(out)

print("== 1. SUPERVISOR-ЯЧЕЙКИ (0o40-0o74) ==")
for a in range(0o40, 0o75):
    print(f"  [{a:04o}] = {O(words[a])}  iso='{iso_text(words[a])}'")

print("\n== 2. MONCARD* = 0o76565 (+25 слов) и окрестность 0o76550-0o76620 ==")
for a in range(0o76550, min(0o76620, N)):
    mark = " <== MONCARD*[%d]" % (a - 0o76565) if 0o76565 <= a < 0o76565 + 25 else ""
    print(f"  [{a:05o}] = {O(words[a])}  iso='{iso_text(words[a])}'{mark}")

print("\n== 3. БУФЕР 76000: слова 0..0o30 ==")
for a in range(0o76000, 0o76030):
    print(f"  [{a:05o}] = {O(words[a])}  iso='{iso_text(words[a])}'")

print("\n== 4. ПОИСК СЛОВА-ЗАПОЛНИТЕЛЯ (все 48-бит значения) ==")
targets = {
    0o1002004010020012: "заполнитель+EOR (находка автора)",
    0o1002004010020040: "заполнитель 4001/з0o504 (без EOR)",
    0o200000003600012:  "[М5] класс [6435]^K",
    0o200000001200012:  "[М5] класс [6365]^K",
    0o4201000001300412: "[М5] класс [6373]^K",
    0o200000001600012:  "[М5] класс [6401]^K",
    0o200000000500012:  "[М5] класс [6363]^K",
    0o7760000000000012: "конец потока (маска LOG 12)",
    0o3000000000000000: "[11200] маркер конец листа",
    0o6000000000000000: "[11201] маркер продолжение",
}
for val, name in targets.items():
    hits = [i for i, w in enumerate(words) if w == val]
    if hits:
        s = " ".join("%05o" % h for h in hits[:12])
        extra = "" if len(hits) <= 12 else " (+%d)" % (len(hits) - 12)
        print(f"  {O(val)} {name}: {s}{extra}")
    else:
        print(f"  {O(val)} {name}: НЕТ")
