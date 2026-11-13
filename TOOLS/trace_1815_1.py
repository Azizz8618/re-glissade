#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# п.18.15(1): проследить в МТР k46-mtr17xx путь ВСDREAD*#1 (стр.371267) ->
# ВСDВЕГ* 03116 -> форматный разбор 5I5 -> должен быть store в 01121-01125.
# Найти место обрыва.
import gzip, re, sys, collections

TRACE = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/z/my-project/re-glissade/RUNS/run-2026-11-13g/k46-mtr17xx/mtr.txt.gz"
START = int(sys.argv[2]) if len(sys.argv) > 2 else 371267   # 1-based строка ВСDREAD*#1
END   = int(sys.argv[3]) if len(sys.argv[3:]) else 441169

LINE = re.compile(
    r"^MTR (\d+)([LR]) (\w{3})\s+([-\d\w]+)(?:\((\d+)\))?"
    r" AU=(\d+) M:(.*)$")

def octv(s):
    try: return int(s, 8)
    except ValueError: return None

def full(a, i):
    if a is None: return None
    return a if i == 0 else (a + i) & 0o177777

stores_vars = []        # записи в 01121..01131 (по AU): (line, pc, op, au, acc)
pcs_after = []          # компактная карта исполненных PC
events = []             # ключевые события
hist = collections.Counter()

with gzip.open(TRACE, "rt", encoding="utf-8", errors="replace") as f:
    for no, line in enumerate(f, 1):
        if no < START: continue
        if no > END: break
        m = LINE.match(line.rstrip("\n"))
        if not m: continue
        pc, lr, op, a, ix, au_s, mregs = m.groups()
        pc = int(pc, 8)
        au = int(au_s, 8)
        # acc: в трассе нет аккумулятора напрямую; М-строка игнорируем пока
        hist[(pc >> 3) << 3] += 1   # грубая PC-карта
        pcs_after.append((no, pc, lr, op, a, ix, au))
        # ВСDВЕГ* вход
        if pc == 0o3116 and lr == "L":
            events.append((no, "ВСDВЕГ*-вход 03116"))
        # запись в переменные программы 01121-01131
        if 0o1121 <= au <= 0o1131 and op in ("atx", "stx", "xta", "aax", "aex", "xxt", "rte", "its", "ita"):
            stores_vars.append((no, pc, op, oct(au), mregs.strip()))
        if pc == 0o3141 and lr == "L":
            events.append((no, "ветвь u1a 03141"))
        if pc == 0o3220 and lr == "L":
            events.append((no, "03220 (WSУ*/конец WRITE?)"))
        if pc == 0o2406 and lr == "L":
            events.append((no, "ВСDWRIТ*-вход 02406"))
        if pc == 0o1132 and lr == "L":
            events.append((no, "ВСDREAD*-вход 01132"))
        if pc == 0o1023 or pc == 0o1025:
            if lr == "L": events.append((no, "конвейер 0%o" % pc))

print("=== ПК-карта после строки %d (по 8-границам, топ-40):" % START)
for pc, c in hist.most_common(40):
    print("  0%04o: %d" % (pc, c))

print("\n=== События:")
for no, ev in events:
    print("  строка %d: %s" % (no, ev))

print("\n=== Записи в 01121-01131 (переменные программы):")
if not stores_vars:
    print("  НЕТ НИ ОДНОЙ")
for no, pc, op, au, mr in stores_vars[:60]:
    print("  строка %d: 0%04o %s %s" % (no, pc, op, au))
if len(stores_vars) > 60:
    print("  ... всего %d" % len(stores_vars))

# Сводка по диапазонам PC для контроля: где исполнение после ВСDREAD*#1
print("\n=== Суммарно по диапазонам PC:")
bands = collections.Counter()
for (no, pc, lr, op, a, ix, au) in pcs_after:
    if   pc < 0o1000: bands["000xx-077x (супервизор/чтец)"] += 1
    elif pc < 0o1200: bands["01000-01177 (оверлей/ВСDREAD*)"] += 1
    elif pc < 0o1400: bands["01200-01377 (тело программы)"] += 1
    elif pc < 0o2000: bands["01400-01777 (FT-обёртки)"] += 1
    elif pc < 0o3000: bands["02000-02777 (сервисы МОНЫ)"] += 1
    elif pc < 0o3200: bands["03000-03177 (ВСDВЕГ*/STOP)"] += 1
    else: bands["03200+ (WSY и др.)"] += 1
for k in sorted(bands): print("  %s: %d" % (k, bands[k]))
