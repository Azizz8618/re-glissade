#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-7 п.18.2: seed k4 - тело = дословные слова сырого спула
(m20/тракт 4, сл.0o147-0o161: *execute, карты данных RLE, *END FILE,
слово конца потока) + эталон-голова + MARK_END.
Использование: mk_seed_k4.py <dd.m20-дамп> <out-seed.bin> [ drum(020) tract(04) ]"""
import sys, re, gzip, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mk_drum_seed import HEADER, CONV_CMD, CONV_DATA, MARK_CONT, MARK_END

def parse_dd_words(path):
    """-> {adr: word} из dispak --drum-dump файла (сжатого или нет)."""
    op = gzip.open if path.endswith('.gz') else open
    words = {}
    with op(path, 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.match(r'^[кс]\s+.*;\s*([0-7]+)\s*$', line.strip())
            if not m:
                continue
            a = int(m.group(1), 8)
            m2 = re.search(r'с\s+([0-7]+)\s+([0-7]+)\s+([0-7]+)\s+([0-7]+)\s*;', line)
            w = 0
            if m2:
                for g in m2.groups():
                    w = (w << 12) | int(g, 8)
            words[a] = w
    return words

def main():
    dd, out = sys.argv[1], sys.argv[2]
    words = parse_dd_words(dd)
    body = []
    for a in range(0o147, 0o162):        # *execute .. слово конца потока
        body.append(words.get(a, 0))
    conv = [CONV_DATA] * len(body)
    recs = []
    for name, rec_words in (('данные', body), ('конец', [])):
        zone = [0] * 1024
        cv = [0] * 1024
        for i, w in enumerate(HEADER):
            zone[i] = w
            cv[i] = CONV_CMD
        zone[0o12] = MARK_CONT if name == 'данные' else MARK_END
        cv[0o12] = CONV_CMD
        pos = 0o14
        for w in rec_words:
            zone[pos] = w; cv[pos] = CONV_DATA; pos += 1
        if name == 'данные':
            zone[pos] = MARK_END; cv[pos] = CONV_DATA; pos += 1
        recs.append((zone, cv))
    with open(out, 'wb') as f:
        for zone, cv in recs:
            for w in zone:
                f.write(w.to_bytes(6, 'big'))
            for c in cv:
                f.write(bytes([c]))
    print(f'k4: тело = слова 0o147-0o161 сырого спула ({len(body)} слов), '
          f'до слова {oct(pos)}')

if __name__ == '__main__':
    main()
