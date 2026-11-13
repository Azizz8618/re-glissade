#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-9 п.18.10(1): seed k12 - конверт из цепочки записей по 0o32.

По реверсу читателя (п.18.9в) границы записей = 0o12 + 0o32*k:
0o12 -> 0o44 -> 0o76 -> 0o130 ...  Запись i = маркер@b_i + слова
[b_i+1 .. b_{i+1}-1] (0o31 = 25 слов). На каждой границе записи стоит
маркер [11201] (лист продолжается), на границе за последней записью -
[11200] (конец листа).

Текст записи = очередная карта колоды (после *execute, включая
*end file) как enc_iso_words: 12 слов ISO (72 кол.) + эталон EOR,
хвост записи до границы - филлер ISO-пробелов (стиль k8:
0o1002004010020040). Первое слово тела [0o13] = вес головы
0o3400000000000000 - как в k1/k8 (18.9в: "ключ@граница+1").

Конволюция: голова+маркер@0o12 = 1 (CONV_CMD), тело = 2 (CONV_DATA),
включая маркеры на поздних границах и [11200] - как в k8 (читатель
классифицировал [76044] c conv=2 как тип 0). Хвост зоны после [11200]
и запись 1 (тракт 5) = нули, в записи 1 маркер конца [11200]@0o12
(conv=1) - стиль mk_seed_k7/mk_drum_seed.

Использование: mk_seed_k12.py <колода> <out>
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk_drum_seed import (HEADER, CONV_CMD, CONV_DATA, MARK_CONT, MARK_END,
                          enc_iso_words, read_data_cards)

FILLER = 0o1002004010020040   # 6 ISO-пробелов (филлер k8)
BOUND0 = 0o12                 # первая граница (маркер головы)
STEP   = 0o32                 # шаг границы (п.18.9в), НЕ 0o31

def main():
    deck, out = sys.argv[1], sys.argv[2]
    zone = [0] * 1024
    cv = [0] * 1024
    for i, w in enumerate(HEADER):
        zone[i] = w; cv[i] = CONV_CMD
    zone[BOUND0] = MARK_CONT; cv[BOUND0] = CONV_CMD

    cards = read_data_cards(deck)          # карты после *execute + *end file
    bounds = [BOUND0 + STEP * (i + 1) for i in range(len(cards))]
    if bounds and bounds[-1] >= 1024:
        print('! записи не умещаются в зону')
        return
    pos = BOUND0 + 1                       # тело с 0o14 (слово 0o13 = вес головы)
    for i, text in enumerate(cards):
        b_next = bounds[i]
        nfill = b_next - pos
        ws = enc_iso_words(text)           # 13 слов: 12 текста + EOR
        if len(ws) > nfill:
            print(f'! карта {i+1} ({len(ws)} сл.) не лезет в запись '
                  f'({nfill} сл.)'); return
        ws += [FILLER] * (nfill - len(ws))
        for w in ws:
            zone[pos] = w; cv[pos] = CONV_DATA; pos += 1
        zone[b_next] = MARK_END if i == len(cards) - 1 else MARK_CONT
        cv[b_next] = CONV_DATA
        pos = b_next + 1

    # запись 1 (тракт 5): нули + [11200]@0o12 (конец потока на следующей зоне)
    z2 = [0] * 1024; c2 = [0] * 1024
    z2[0o12] = MARK_END; c2[0o12] = CONV_CMD

    with open(out, 'wb') as f:
        for zn, cc in ((zone, cv), (z2, c2)):
            for w in zn:
                f.write(w.to_bytes(6, 'big'))
            for c in cc:
                f.write(bytes([c]))
    print(f'k12: границы {["%o" % b for b in bounds]} '
          f'(записей: {len(cards)} + [11200]@{oct(bounds[-1])}), '
          f'тело до {oct(pos)} -> {out}')
    for a in (BOUND0, 0o13, 0o14, bounds[0], bounds[1], bounds[-1]):
        print(f'  [{a:04o}] = {zone[a]:016o} conv={cv[a]}')

if __name__ == '__main__':
    main()
