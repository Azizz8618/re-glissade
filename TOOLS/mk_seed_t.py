#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t-серия (13.11, сессия продолжения): варианты слова-класса записи [0o13]
и раскладок [класс][карта]. Классы из таблицы классов монread% (Шаг 2д,
class ^ 0o200000000200001). Тело: [заголовок 0o0-0o12][маркер@0o12][тело].

Варианты:
  t1  [0o13] = класс^K [6435]           (остальное как h)
  t2  [0o13] = класс raw [6435]
  t3  [0o13] = слово конца потока
  t4  [0o13] = 0o4000000000000000
  t6  записи = [класс^K 6435][карта 13 слов]   (*END FILE - тот же класс)
  t7  ... *END FILE - класс 6365^K
  t8  ... *END FILE - класс 6401^K
  t9  записи = [класс 6435^K][карта 12 слов][класс 6435^K] (класс=терминатор)
  t10 ... *END FILE - 6365^K
  t11 ... класс 6373^K (все записи)
  t12 ... класс 6363^K (все записи)

Использование: mk_seed_t.py <колода.b6> <seed-файл> <вариант>
"""
import sys

C = {  # классы [N] (raw) и class^K
    'K': 0o200000000200001,
    6435: 0o0000000003400013, 6365: 0o0000000001000013,
    6373: 0o4001000001100413, 6401: 0o0000000001400013,
    6363: 0o0000000000700013,
}
def ck(n): return C[n] ^ C['K']

def enc12(text, ISO, pack):
    chars = [ISO.get(c, 0o40) for c in text.upper().ljust(72)]
    return pack(chars, 8, ISO[' '])

def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location('m', __file__.replace('mk_seed_t.py', 'mk_drum_seed_h.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    deck, out, variant = sys.argv[1], sys.argv[2], sys.argv[3]
    cards = m.read_data_cards(deck)
    data_cards = [c for c in cards if not c.strip().upper().startswith('*END FILE')]

    def build():
        zone = [0]*1024; conv = [0]*1024
        for i, w in enumerate(m.HEADER):
            zone[i] = w; conv[i] = m.CONV_CMD
        zone[0o12] = m.MARK_CONT; conv[0o12] = m.CONV_CMD
        pos = 0o13
        if variant in ('t1', 't2', 't3', 't4'):
            w13 = {'t1': ck(6435), 't2': C[6435],
                   't3': 0o7760000000000012, 't4': 0o4000000000000000}[variant]
            zone[0o13] = w13; conv[0o13] = m.CONV_CMD
            pos = 0o14
            for c in data_cards + ['*end file']:
                for w in m.enc_iso_words(c):
                    zone[pos] = w; conv[pos] = m.CONV_DATA; pos += 1
        elif variant in ('t6', 't7', 't8'):
            cls = ck(6435)
            end = {'t6': cls, 't7': ck(6365), 't8': ck(6401)}[variant]
            for c in data_cards:
                zone[pos] = cls; conv[pos] = m.CONV_CMD; pos += 1
                for w in m.enc_iso_words(c):
                    zone[pos] = w; conv[pos] = m.CONV_DATA; pos += 1
            zone[pos] = end; conv[pos] = m.CONV_CMD; pos += 1
            for w in m.enc_iso_words('*end file'):
                zone[pos] = w; conv[pos] = m.CONV_DATA; pos += 1
        else:  # t9..t12: карта 12 слов + класс-терминатор
            cls = {'t9': ck(6435), 't10': ck(6435), 't11': ck(6373),
                   't12': ck(6363)}[variant]
            endc = {'t9': cls, 't10': ck(6365), 't11': cls, 't12': cls}[variant]
            zone[pos] = cls; conv[pos] = m.CONV_CMD; pos += 1
            for c in data_cards:
                for w in enc12(c, m.ISO, m.pack):
                    zone[pos] = w; conv[pos] = m.CONV_DATA; pos += 1
                zone[pos] = cls; conv[pos] = m.CONV_CMD; pos += 1
            for w in enc12('*end file', m.ISO, m.pack):
                zone[pos] = w; conv[pos] = m.CONV_DATA; pos += 1
            zone[pos] = endc; conv[pos] = m.CONV_CMD; pos += 1
        zone[pos] = m.MARK_END; conv[pos] = m.CONV_DATA; pos += 1
        return zone, conv, pos

    with open(out, 'wb') as f:
        for (zone, conv, pos) in (build(), build()):
            for w in zone: f.write(w.to_bytes(6, 'big'))
            for c in conv: f.write(bytes([c]))
    print(f'{variant}: ok')

if __name__ == '__main__':
    main()
