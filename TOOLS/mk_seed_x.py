#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Серия x: конверт-цепочка - по ЗАПИСИ на тракт.

Гипотеза п.16.9(а): монread% идёт по ТРАКТАМ ([КCOUNT+3]++ + Э70);
маркер [11201] в сл.0o12 заголовка = 'есть продолжение на следующем
тракте'. Наш seed 'h' клал 2 карты + *END FILE в ОДИН конверт.
Вариант x3: каждый конверт = заголовок + ОДНА запись + [11201]/[11200]
в сл.0o12; тело без внутренних маркеров.

Использование: mk_seed_x.py <колода.b6> <seed-файл> <вариант>
                [барабан(восьм.)] [тракт(восьм.)]
Варианты:
  x1 = как 'h', но БЕЗ [11200] в конце тела (только в сл.0o12)
  x3 = по записи на тракт: карта1 | карта2 | *END FILE
  x4 = как x3, но карта = ГОСТ-6бит (10 слов) вместо ISO
"""
import sys

sys.path.insert(0, '/home/z/my-project/re-glissade/TOOLS')
from mk_drum_seed_h import (HEADER, MARK_CONT, MARK_END, CONV_CMD, CONV_DATA,
                            read_data_cards, enc_iso_words, enc_gost_words,
                            enc_iso_var, pack, ISO, EOR, WORD_EOR, SP)


def build_x(deck, mode, record, gost=False):
    """Один конверт: заголовок (сл.0o12 = MARK_CONT/MARK_END) + запись."""
    zone = [0] * 1024
    conv = [0] * 1024
    for i, w in enumerate(HEADER):
        zone[i] = w
        conv[i] = CONV_CMD
    last = (mode == 'end')
    zone[0o12] = MARK_END if last else MARK_CONT
    conv[0o12] = CONV_CMD
    if last and record is None:
        return zone, conv, 0o14
    pos = 0o14
    if mode == 'end':
        # конверт конца: пустое тело
        return zone, conv, pos
    enc = enc_gost_words if gost else enc_iso_words
    for w in enc(record):
        zone[pos] = w
        conv[pos] = CONV_DATA
        pos += 1
    return zone, conv, pos


def build_x1(deck):
    """Как 'h', но тело без [11200]; сл.0o12 = [11200] (конец потока)."""
    zone = [0] * 1024
    conv = [0] * 1024
    for i, w in enumerate(HEADER):
        zone[i] = w
        conv[i] = CONV_CMD
    zone[0o12] = MARK_END
    conv[0o12] = CONV_CMD
    pos = 0o14
    for c in read_data_cards(deck):
        for w in enc_iso_words(c):
            zone[pos] = w
            conv[pos] = CONV_DATA
            pos += 1
    return zone, conv, pos


def main():
    deck, out, variant = sys.argv[1], sys.argv[2], sys.argv[3]
    cards = read_data_cards(deck)
    data = [c for c in cards if not c.strip().upper().startswith('*END FILE')]
    recs = []
    if variant == 'x1':
        recs = [build_x1(deck)]
    elif variant in ('x3', 'x4'):
        gost = (variant == 'x4')
        for c in data:
            recs.append(build_x(deck, 'data', c, gost))
        recs.append(build_x(deck, 'data', '*end file', gost))
        recs.append(build_x(deck, 'end', None, gost))
    else:
        raise SystemExit('вариант: x1|x3|x4')
    with open(out, 'wb') as f:
        for zone, conv, pos in recs:
            for w in zone:
                f.write(w.to_bytes(6, 'big'))
            for c in conv:
                f.write(bytes([c]))
    print(f'вариант {variant}: {len(recs)} конвертов (тракты подряд); '
          f'карт данных {len(data)}')


if __name__ == '__main__':
    main()
