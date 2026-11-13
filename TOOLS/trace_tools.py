#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Парсер MTR-трассы dispak (BESM6_MTR) для реверса читателя МОНА-80.

Формат строки:
MTR <pc><L|R> <op> <addr>(<idx>) AU=<hex...> M: 01=.. 02=.. ... 16=.. R16=.. R17=..
"""
import re
import sys

LINE = re.compile(
    r'^MTR\s+(\S+)L?(\S+)\s+(\S+)\s+(\S+)\((\S+)\)\s+AU=(\S+)\s+M:\s+(.*)$'
)
REGS = re.compile(r'(\d\d)=([0-7]+)')

def parse_line(s):
    m = LINE.match(s)
    if not m:
        return None
    pc = m.group(1)
    op, addr, idx = m.group(3), m.group(4), m.group(5)
    regs = {}
    for k, v in REGS.findall(m.group(7)):
        regs[int(k)] = int(v, 8)
    return dict(pc=pc, lr=m.group(2), op=op, addr=int(addr, 8), idx=idx,
                au=m.group(6), regs=regs)

def ea(line):
    """Исполнительный адрес: addr + индекс-регистр (без супервизора)."""
    try:
        i = int(line['idx'])
    except ValueError:
        return line['addr']
    r = line['regs'].get(i, 0)
    return (line['addr'] + r) & 0o77777

def main():
    path = sys.argv[1]
    cmd = sys.argv[2]
    lines = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for n, s in enumerate(f, 1):
            p = parse_line(s.rstrip('\n'))
            if p:
                p['n'] = n
                lines.append(p)

    if cmd == 'ea':          # все обращения с EA в диапазоне
        lo, hi = int(sys.argv[3], 8), int(sys.argv[4], 8)
        for p in lines:
            a = ea(p)
            if lo <= a <= hi and p['op'] not in ('uj', 'ujm', 'vjm', 'vlm',
                                                 'vzm', 'v1m', 'u1m', 'uza',
                                                 'u1a', 'stop', 'vtm', 'utm',
                                                 'm+j', 'mtj', 'vj+m'):
                print(f"{p['n']:7d} {p['pc']:>5}{p['lr']} {p['op']:<5} "
                      f"EA={a:05o} idx={p['idx']:<2} M1={p['regs'].get(1,0):05o} "
                      f"M4={p['regs'].get(4,0):05o} M5={p['regs'].get(5,0):05o}")
    elif cmd == 'reg':       # история регистра: печать строк, где reg изменился
        r = int(sys.argv[3])
        prev = None
        for p in lines:
            v = p['regs'].get(r)
            if v is not None and v != prev:
                print(f"{p['n']:7d} {p['pc']:>5}{p['lr']} {p['op']:<5} "
                      f"{p['addr']:05o}({p['idx']}) M{r}={v:05o}")
                prev = v
    elif cmd == 'slice':     # сырой срез строк N..M
        lo, hi = int(sys.argv[3]), int(sys.argv[4])
        for p in lines:
            if lo <= p['n'] <= hi:
                rs = ' '.join(f"M{k:02d}={v:05o}" for k, v in
                              sorted(p['regs'].items()))
                print(f"{p['n']:7d} {p['pc']:>5}{p['lr']} {p['op']:<5} "
                      f"{p['addr']:05o}({p['idx']}) AU={p['au']} {rs}")
    elif cmd == 'find':      # первый/все pc==X
        pc = sys.argv[3]
        cnt = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        k = 0
        for p in lines:
            if p['pc'] == pc:
                rs = ' '.join(f"M{i:02d}={v:05o}" for i, v in
                              sorted(p['regs'].items()))
                print(f"{p['n']:7d} {p['pc']:>5}{p['lr']} {p['op']:<5} "
                      f"{p['addr']:05o}({p['idx']}) AU={p['au']} {rs}")
                k += 1
                if k >= cnt:
                    break
    else:
        sys.exit('commands: ea <lo> <hi> | reg <r> | slice <n> <m> | '
                 'find <pc> [cnt]')

if __name__ == '__main__':
    main()
