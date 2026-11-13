#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s7-эксперимент (13.11): конверт, подгаданный под указатель МОНИТОРА.
КCOUNT*[0] = [0600] = 0o76062: резидентный монread% МОНИТОРА разбирает
лист со слова 0o62 буфера. Раскладываем конверт в спуле (tract 4) так,
чтобы ПЕРВАЯ КАРТА ДАННЫХ начиналась ровно со слова 0o62:
  [0..0o11]  заголовок (0o22015 + 11 весов, маркер@0o12=[11201])
  [0o14..0o61] заполнитель (пробелы)
  [0o62..]   записи карт: [12 слов текста + WORD_EOR] x N
             затем *END FILE, слово конца потока 0o7760000000000012.
Записи упакованы подряд (без 25-словных границ): разбор масками
монread% пропускает служебные и копирует текст до EOR-слова.
"""
import sys

SP6 = 0o404040404040          # '      ' - 6 пробелов ISO
EOR_BYTE = 0o12
MARK_CONT = 0o6000000000000000   # [11201]
WORD_EOR  = 0o1002004010020012   # 5 пробелов + EOR (эталон [М1+211])
WORD_END  = 0o7760000000000012   # конец потока (как в спуле МОНИТОРА)
POS_START = 0o14                 # куда смотрит КCOUNT*[0]=[0600]

HEADER = [0o0000000000022015,
          0o6400000000000000, 0o6000000000000000, 0o5400000000000000,
          0o5000000000000000, 0o4400000000000000, 0o4000000000000000,
          0o1400000000000000, 0o2000000000000000, 0o2400000000000000,
          0o3000000000000000, 0o3400000000000000]

ISO = {' ': 0o40, '!': 0o41, '"': 0o42, '#': 0x23, '$': 0x24, '%': 0x25,
       '&': 0x26, "'": 0x27, '(': 0x28, ')': 0x29, '*': 0x2A, '+': 0x2B,
       ',': 0x2C, '-': 0x2D, '.': 0x2E, '/': 0x2F, ':': 0x3A, ';': 0x3B,
       '<': 0x3C, '=': 0x3D, '>': 0x3E, '?': 0x3F, '@': 0x40}
for i in range(10):
    ISO[chr(ord('0') + i)] = 0o60 + i
for i in range(26):
    ISO[chr(ord('A') + i)] = 0o101 + i
    ISO[chr(ord('a') + i)] = 0o101 + i


def enc_card(text, width=72):
    """Карта -> 13 слов: 12 слов текста (72 колонки) + WORD_EOR."""
    chars = [ISO.get(c, 0o40) for c in text.upper().ljust(width)]
    words = []
    for w in range(0, len(chars), 6):
        v = 0
        for c in chars[w:w+6]:
            v = (v << 8) | c
        words.append(v)
    words.append(WORD_EOR)
    return words


def build_zone(cards):
    zone = [0] * 1024
    conv = [0] * 1024
    for i, w in enumerate(HEADER):
        zone[i] = w
        conv[i] = 1
    zone[0o12] = MARK_CONT
    conv[0o12] = 1
    for i in range(0o14, POS_START):
        zone[i] = SP6
        conv[i] = 2
    pos = POS_START
    for c in cards:
        for w in enc_card(c):
            zone[pos] = w; conv[pos] = 2; pos += 1
    zone[pos] = WORD_END; conv[pos] = 2; pos += 1
    return zone, conv, pos


def main():
    cards = sys.argv[1:]
    zone, conv, pos = build_zone(cards)
    with open('/tmp/seed-s7.bin', 'wb') as f:
        for w in zone:
            f.write(w.to_bytes(6, 'big'))
        for c in conv:
            f.write(bytes([c]))
    print(f"карты-с-0o14: {cards}")
    print(f"тело с {oct(POS_START)} (dec {POS_START}), до слова {oct(pos)}")
    for w in (0, 0o12, 0o14, POS_START):
        print(f"  [{w:03o}] = {zone[w]:016o}")


if __name__ == '__main__':
    main()
