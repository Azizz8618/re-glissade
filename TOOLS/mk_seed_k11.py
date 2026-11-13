#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-7 п.18.2: seed k11 - многотрактный конверт: тело не кончается
на тракте 4, а продолжается на тракте 5 (без заголовка): tract 4 =
заголовок + тело 0o14-0o777 (карты+эталоны), tract 5 = продолжение тела
(пробелы-заполнители + эталон + MARK_END).
Использование: mk_seed_k11.py <колода> <out>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk_drum_seed import (HEADER, CONV_CMD, CONV_DATA, MARK_CONT, MARK_END,
                          WORD_EOR, enc_iso_words, read_data_cards)

def main():
    deck, out = sys.argv[1], sys.argv[2]
    rec1 = [0] * 1024; cv1 = [0] * 1024
    rec2 = [0] * 1024; cv2 = [0] * 1024
    for i, w in enumerate(HEADER):
        rec1[i] = w; cv1[i] = CONV_CMD
    rec1[0o12] = MARK_CONT; cv1[0o12] = CONV_CMD
    pos = 0o14
    for text in read_data_cards(deck):
        for w in enc_iso_words(text):
            if pos < 1024:
                rec1[pos] = w; cv1[pos] = CONV_DATA; pos += 1
    # хвост тракта 4: заполнители-пробелы до конца зоны (тело продолжается)
    while pos < 1024:
        rec1[pos] = 0o404040404040; cv1[pos] = CONV_DATA; pos += 1
    # тракт 5 = продолжение: пробелы + эталон + конец потока [11200]
    p2 = 0
    for _ in range(4):
        rec2[p2] = 0o404040404040; cv2[p2] = CONV_DATA; p2 += 1
    rec2[p2] = WORD_EOR; cv2[p2] = CONV_DATA; p2 += 1
    rec2[p2] = MARK_END; cv2[p2] = CONV_DATA; p2 += 1
    with open(out, 'wb') as f:
        for zn, cc in ((rec1, cv1), (rec2, cv2)):
            for w in zn:
                f.write(w.to_bytes(6, 'big'))
            for c in cc:
                f.write(bytes([c]))
    print(f'k11: тракт 4 = тело до конца зоны (0o1777), тракт 5 = '
          f'продолжение до {oct(p2)}')

if __name__ == '__main__':
    main()
