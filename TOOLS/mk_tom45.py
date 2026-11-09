#!/usr/bin/env python3
# Этап 1 (А1/А2): формирование тома 202 (входной поток ЛУН 45) в формате
# записи МОNRЕАД* Монитора-80: зона = 1024 слова; карта = 12 слов x 8 симв.
# ГОСТ 10859 (6 бит) = 96 символов (80 колонок + добивка пробелами).
# Использование: mk_tom45.py <колода.b6> <файл тома 202>

import sys

def read_data_cards(deck_path):
    cards = []
    in_data = False
    with open(deck_path, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\r\n').rstrip('\x00')
            if not in_data:
                if line.strip().lower().startswith('*execute'):
                    in_data = True
                continue
            cards.append(line)
            if line.strip().lower().startswith('*end file'):
                break
    if not cards or not cards[-1].strip().lower().startswith('*end file'):
        cards.append('*end file')
    return cards

# ГОСТ 10859 (6 бит), по таблицам dispak encoding.c (gost_to_unicode_*):
# 000-011: 0-9; 012:+ 013:- 014:/ 015:, 016:. 017:пробел
# 020-037: спец; 031:'*'
# 040-076: кириллица А..Я (в режиме cyr); 077:D; 100-133: латинские F,G,I,J,L,N,Q,R,S,U,V,W,X,Z
GOST = {}
for i in range(0, 10):
    GOST[chr(ord('0') + i)] = i
GOST.update({'+': 0o12, '-': 0o13, '/': 0o14, ',': 0o15, '.': 0o16, ' ': 0o17})
GOST.update({'(': 0o22, ')': 0o23, '=': 0o25, ';': 0o26, '[': 0o27, ']': 0o30,
             '*': 0o31, '<': 0o34, '>': 0o35, ':': 0o36, "'": 0o33, '!': 0o135,
             '"': 0o136})
CYR = 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЫЬЭЮЯ'
for i, ch in enumerate(CYR):
    GOST[ch] = 0o40 + i
    GOST[ch.lower()] = 0o40 + i
LAT = 'DFGIJLNQRSUVWXZ'
for i, ch in enumerate(LAT):
    GOST[ch] = 0o77 + i
    GOST[ch.lower()] = 0o77 + i
GOST.setdefault('#', 0o20)      # чуть не то, но редко встречается
GOST.setdefault("'", 0o33)

def enc_card(text):
    s = (text + ' ' * 96)[:96]
    words = []
    for w in range(12):
        v = 0
        for c in s[w * 8:(w + 1) * 8]:
            v = (v << 6) | GOST.get(c, 0o17)
        words.append(v)
    return words

def main():
    deck, tom = sys.argv[1], sys.argv[2]
    cards = read_data_cards(deck)
    print(f'карт данных: {len(cards)}')
    zone = []
    for c in cards:
        words = enc_card(c)
        zone.extend(words)
        # контрольная печать первых слов карты
    print('слов карты всего:', len(zone))
    full = zone + [0] * (1024 - len(zone))
    assert len(full) == 1024
    with open(tom, 'wb') as f:
        for w in full:
            f.write(w.to_bytes(6, 'big'))
    print('записан', tom, '=', 1024 * 6, 'байт')
    # печать первых двух карт для контроля
    for ci, c in enumerate(cards[:3]):
        words = enc_card(c)
        print(f'карта {ci}: {c!r}')
        print('  слова:', ' '.join(f'{w:016o}' for w in words[:3]))

if __name__ == '__main__':
    main()
