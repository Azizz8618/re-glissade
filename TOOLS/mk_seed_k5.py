#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-7 п.18.2: seed k5 - гибрид: RLE-карты сырого спула дословно +
слово-эталон EOR (0o1002004010020012) после каждой карты.
Разбиение тела сырого спула (m20/т4): *execute 0o147-0o150, карта 1
0o151-0o153, карта 2 0o154-0o156, *END FILE 0o157-0o160, конец 0o161.
Вариант A (k5): без *execute, карты+эталоны; Вариант B (k6): с *execute.
Использование: mk_seed_k5.py <dd.m20> <out5> <out6>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk_drum_seed import HEADER, CONV_CMD, CONV_DATA, MARK_CONT, MARK_END, \
    WORD_EOR
from mk_seed_k4 import parse_dd_words

def build(body_groups, out):
    recs = []
    for name, cont in (('данные', True), ('конец', False)):
        zone = [0] * 1024
        cv = [0] * 1024
        for i, w in enumerate(HEADER):
            zone[i] = w
            cv[i] = CONV_CMD
        zone[0o12] = MARK_CONT if cont else MARK_END
        cv[0o12] = CONV_CMD
        pos = 0o14
        for grp in body_groups:
            for a in grp:
                zone[pos] = a; cv[pos] = CONV_DATA; pos += 1
            if cont:                     # эталон после каждой группы
                zone[pos] = WORD_EOR; cv[pos] = CONV_DATA; pos += 1
        if cont:
            zone[pos] = MARK_END; cv[pos] = CONV_DATA; pos += 1
        recs.append((zone, cv, pos))
    with open(out, 'wb') as f:
        for zone, cv, pos in recs:
            for w in zone:
                f.write(w.to_bytes(6, 'big'))
            for c in cv:
                f.write(bytes([c]))
    return recs[0][2]

def main():
    dd, out5, out6 = sys.argv[1], sys.argv[2], sys.argv[3]
    w = parse_dd_words(dd)
    g = lambda a, b: [w[x] for x in range(a, b + 1)]
    execute = g(0o147, 0o150)
    card1 = g(0o151, 0o153)
    card2 = g(0o154, 0o156)
    endfile = g(0o157, 0o160)
    kend = g(0o161, 0o161)
    p5 = build([card1, card2, endfile], out5)
    p6 = build([execute, card1, card2, endfile], out6)
    print(f'k5 (без *execute): тело до {oct(p5)}, k6 (с *execute): до {oct(p6)}')

if __name__ == '__main__':
    main()
