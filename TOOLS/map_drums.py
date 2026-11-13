#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-7 п.18: карта барабанов m20/m21 из run-2026-11-13d.
(1) сводка непустых областей по трактам (зоны по 1024 слова = 0o2000);
(2) поиск слов-кандидатов: головы h-конверта [0504]-[0507]
    (0o5444040070000000, 0o5465310071000000, 0o5547250074000000,
     0o5504310072000000), записей таблицы спула 0o4021xxxx/0o4020xxxx/
    0o4100xxxx/0o4401xxxx и слова конца потока 0o7760000000000012;
(3) печать окон вокруг находок (ISO+ГОСТ).
Запуск: python3 map_drums.py DD20 DD21"""
import sys, re
sys.path.insert(0, '.')
from parse_dd import iso_str, gost_str, parse

HEAD = [0o5444040070000000, 0o5465310071000000,
        0o5547250074000000, 0o5504310072000000]
ENDW = 0o7760000000000012

def hi12(w):
    """старшие 12 бит слова (код типа слова спула/конверта)"""
    return (w >> 48) & 0o7777

def main(dd20, dd21):
    drums = [('m20 (020)', parse(dd20)), ('m21 (021)', parse(dd21))]
    for name, zones in drums:
        print(f'===== {name} =====')
        # (1) карта непустых трактов
        for z in sorted(zones):
            nz = [w for _, w in zones[z] if w != 0]
            if nz:
                lo = min(a for a, w in zones[z] if w != 0)
                hi = max(a for a, w in zones[z] if w != 0)
                print(f'  тракт {z:o}: непустых слов {len(nz):4d} '
                      f'(диапазон {lo:05o}..{hi:05o})')
            else:
                print(f'  тракт {z:o}: ПУСТ')
        # (2) поиск ключевых слов
        print('  --- поиск головы h-конверта [0504]-[0507] ---')
        for z in sorted(zones):
            for adr, w in zones[z]:
                if w in HEAD:
                    print(f'  НАЙДЕНО тракт {z:o} сл.{adr:05o}: {w:016o} '
                          f' {iso_str(w)} |{gost_str(w)}|')
        print('  --- поиск слова конца потока 0o7760000000000012 ---')
        for z in sorted(zones):
            for adr, w in zones[z]:
                if w == ENDW:
                    print(f'  НАЙДЕНО тракт {z:o} сл.{adr:05o}: {w:016o}')
        print('  --- слова с кодом старших 12 бит 0o4021/0o4020/0o4100/0o4401 ---')
        hits = 0
        for z in sorted(zones):
            for adr, w in zones[z]:
                h = hi12(w)
                if h in (0o4021, 0o4020, 0o4100, 0o4401):
                    print(f'  тракт {z:o} сл.{adr:05o}: {w:016o} {iso_str(w)}')
                    hits += 1
        if not hits:
            print('  (нет)')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
