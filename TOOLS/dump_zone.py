#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-7 п.18.3: дамп зоны образа тома dispak (zone_t: 6144+1024+1088).
Печать: сл., слово (окт.), ISO, ГОСТ, конволют-байт.
Запуск: python3 dump_zone.py <образ> <зона> [первое-слово] [последнее]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_dd import iso_str, gost_str

ZONE = 8256

def main():
    img, z = sys.argv[1], int(sys.argv[2], 0)
    w0 = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0
    w1 = int(sys.argv[4], 0) if len(sys.argv) > 4 else 1024
    total = os.path.getsize(img)
    assert total % ZONE == 0, 'размер не кратен 8256'
    nz = total // ZONE
    assert z < nz, f'зона {z} >= {nz}'
    with open(img, 'rb') as f:
        f.seek(z * ZONE)
        blob = f.read(ZONE)
    print(f'{img}: зона {z} (всего зон {nz}), слова {w0}..{min(w1,1024)-1}:')
    for w in range(w0, min(w1, 1024)):
        v = int.from_bytes(blob[w*6:(w+1)*6], 'big')
        conv = blob[6144 + w]
        chk = blob[7168 + w] if 7168 + w < ZONE else 0
        if v == 0 and conv == 0:
            continue
        print(f'  {w:04o}: {v:016o}  {iso_str(v)}  |{gost_str(v)}|  '
              f'c={conv:03o} k={chk:03o}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
