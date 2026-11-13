#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-7 п.18.2: серия k7-k10 - ключи 25-словных записей.
Тело = seed-h (карты 13 слов с эталоном), НО на границах записей
0o44 + 0o31*k (k=1,2,...) вместо текста ставится КЛЮЧ:
  k7: KEY_REC = 0o200000000200001 (IOCONT*)
  k8: MARK_CONT = 0o6000000000000000 ([11201])
  k9: сл.0 головы = 0o0000000000022015
  k10: слово головы [0504] = 0o5444040070000000
Ключ ставится ЗАМЕЩЕМ слова на границе (запись 1: 0o13+25=0o44 и т.д.).
Использование: mk_seed_k7.py <колода> <каталог-вывода>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk_drum_seed import (HEADER, CONV_CMD, CONV_DATA, MARK_CONT, MARK_END,
                          WORD_EOR, enc_iso_words, read_data_cards)

KEYS = {
    'k7': 0o200000000200001,
    'k8': 0o6000000000000000,
    'k9': 0o0000000000022015,
    'k10': 0o5444040070000000,
}

def build(variant, deck_path):
    key = KEYS[variant]
    zone = [0] * 1024
    cv = [0] * 1024
    for i, w in enumerate(HEADER):
        zone[i] = w
        cv[i] = CONV_CMD
    zone[0o12] = MARK_CONT
    cv[0o12] = CONV_CMD
    cards = read_data_cards(deck_path)
    pos = 0o14
    keys_at = []
    for text in cards:
        ws = enc_iso_words(text)          # 13 слов: 12 текста + эталон
        for w in ws:
            if pos >= 0o44 and (pos - 0o14) % 0o31 == 0o30:
                # граница записи (0o44, 0o75, ...): ключ вместо слова
                zone[pos] = key; cv[pos] = CONV_DATA
                keys_at.append(pos)
                pos += 1
            zone[pos] = w; cv[pos] = CONV_DATA; pos += 1
    zone[pos] = MARK_END; cv[pos] = CONV_DATA; pos += 1
    return zone, cv, pos, keys_at

def main():
    deck, outdir = sys.argv[1], sys.argv[2]
    for variant in KEYS:
        zone, cv, pos, keys_at = build(variant, deck)
        out = os.path.join(outdir, f'seed-{variant}.bin')
        with open(out, 'wb') as f:
            for zn, cc in ((zone, cv), (None, None)):
                if zn is None:
                    zn = [0] * 1024
                    cc = [0] * 1024
                    zn[0o12] = MARK_END; cc[0o12] = CONV_CMD
                for w in zn:
                    f.write(w.to_bytes(6, 'big'))
                for c in cc:
                    f.write(bytes([c]))
        print(f'{variant}: ключи на {["%o" % k for k in keys_at]}, '
              f'тело до {oct(pos)} -> {out}')

if __name__ == '__main__':
    main()
