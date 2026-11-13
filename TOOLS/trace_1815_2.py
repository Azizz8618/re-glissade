#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# п.18.15(1) v2: EA-корректный поиск записей в 01121-01131 (переменные программы)
# в трассе k46-mtr17xx после ВСDREAD*#1 (строка 371267) и в целом по трассе.
# М: колонка = состояние ДО исполнения полукоманды этой строки.
import gzip, re, sys

TRACE = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/z/my-project/re-glissade/RUNS/run-2026-11-13g/k46-mtr17xx/mtr.txt.gz"
START = int(sys.argv[2]) if len(sys.argv) > 2 else 1
END   = int(sys.argv[3]) if len(sys.argv[3:]) else 10**9

LINE = re.compile(
    r"^MTR (\d+)([LR]) (\w{3})\s+([-\d\w]+)(?:\((\d+)\))?"
    r" AU=(\d+) M:(.*)$")
MREG = re.compile(r"(\d\d)=([0-7]+)")
WRITE_OPS = {"stx", "atx", "aax", "aox", "aex", "xxt", "amx", "rte"}

def octv(s):
    try: return int(s, 8)
    except ValueError: return None

writes = []      # (line, pc, lr, op, ea, value)
vts = []         # vtm 112x(5) / mtj - установка цели присваивания
cur = 0
with gzip.open(TRACE, "rt", encoding="utf-8", errors="replace") as f:
    for no, line in enumerate(f, 1):
        if no < START: continue
        if no > END: break
        m = LINE.match(line.rstrip("\n"))
        if not m: continue
        pc, lr, op, a, ix, au_s, mregs = m.groups()
        pc = int(pc, 8)
        addr = octv(a)
        val = octv(au_s)          # операнд (48-бит, может быть > 32K)
        regs = dict((int(k, 8) if len(k)==2 else int(k), octv(v)) for k, v in MREG.findall(mregs))
        # индекс: в трассе 01..16 -> М1..М16 (восьмеричные имена 01..07,10..16)
        if ix is not None and addr is not None:
            iname = int(ix, 8)
            mval = regs.get(iname, 0)
            ea = (addr + mval) & 0o177777
        else:
            ea = addr
        if op in WRITE_OPS and ea is not None and 0o1121 <= ea <= 0o1131:
            writes.append((no, pc, lr, op, ea, val))
        if op == "vtm" and ix == "5" and addr is not None and 0o1100 <= addr <= 0o1200:
            vts.append((no, pc, "vtm 5 <- 0%o" % addr))
        if op == "mtj" and ix == "5":
            vts.append((no, pc, "mtj 16 <- М5=0%o" % (regs.get(5,0) if 5 in regs else regs.get(0o5,0))))

print("=== Записи (EA-корректно) в 01121-01131 после строки %d: %d" % (START, len(writes)))
for no, pc, lr, op, ea, val in writes:
    print("  стр.%d 0%04o%s %s -> [0%o] = 0o%016o" % (no, pc, lr, op, ea, val))

print("\n=== Установки цели присваивания (vtm 112x(5)/mtj 16<-М5): %d" % len(vts))
for no, pc, txt in vts[:80]:
    print("  стр.%d 0%04o %s" % (no, pc, txt))
if len(vts) > 80: print("  ... всего %d" % len(vts))
