#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-7 п.18.3: поиск РЕАЛЬНОГО спула/конверта в образах томов
dispak (формат zone_t: data 6144 + convol 1024 + check 1088 = 8256 Б).
Ищем по всем зонам всех томов:
  (1) слова головы [0504]-[0507] МОНА-80 (0o5444040070000000 и сос.);
  (2) слово1 записи таблицы спула 0o4021374041000012 и любые слова
      с u1=0o4021+k*0o20/u3=0o4100+k*0o100 (юнит-пары);
  (3) маркер [11200]/[11201] в сл.0o12 зоны (контракт IOXXFMR);
  (4) слово конца потока 0o7760000000000012;
  (5) эталон конца карты 0o1002004010020012 (5 пробелов+EOR).
Конволют-байты найденных слов печатаются (тип: данные/команда).
Запуск: python3 scan_images.py <путь-к-каталогу-образов>"""
import sys, os

ZONE = 8256
WORDS = 1024

CAND = {
    0o5444040070000000: 'голова[0504]',
    0o5465310071000000: 'голова[0505]',
    0o5547250074000000: 'голова[0506]',
    0o5504310072000000: 'голова[0507]',
    0o4021374041000012: 'таблица.запись1',
    0o7760000000000012: 'конец-потока',
    0o1002004010020012: 'эталон-EOR',
    0o3000000000000000: 'MARK_END[11200]',
    0o6000000000000000: 'MARK_CONT[11201]',
}

def read_words(buf):
    ws = []
    for w in range(WORDS):
        b = buf[w*6:(w+1)*6]
        v = int.from_bytes(b, 'big')
        ws.append(v)
    return ws

def scan(path):
    total = os.path.getsize(path)
    nz = total // ZONE
    hits = []
    for z in range(nz):
        off = z * ZONE
        data = path_bytes[path][off:off+6144] if False else None
    return hits

def main(d):
    for fname in sorted(os.listdir(d)):
        p = os.path.join(d, fname)
        if not os.path.isfile(p):
            continue
        total = os.path.getsize(p)
        if total % ZONE != 0:
            print(f'{fname}: размер {total} не кратен {ZONE} - пропущен')
            continue
        nz = total // ZONE
        print(f'=== {fname}: {nz} зон ===')
        with open(p, 'rb') as f:
            blob = f.read()
        found = 0
        for z in range(nz):
            base = z * ZONE
            for w in range(WORDS):
                v = int.from_bytes(blob[base+w*6:base+w*6+6], 'big')
                if v in CAND:
                    conv = blob[base+6144+w]
                    # MARK_* на не-0o12 позициях шумят: фильтр контекстный
                    if v in (0o3000000000000000, 0o6000000000000000) and w != 0o12:
                        continue
                    print(f'  з.{z:5d} сл.{w:04o}: {v:016o} {CAND[v]} '
                          f'conv={conv:03o}')
                    found += 1
        if not found:
            print('  (ничего)')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
