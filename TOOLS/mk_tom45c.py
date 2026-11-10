#!/usr/bin/env python3
# Этап 1 (А2, эксперимент v2): том 202 = входной поток ЛУН 45.
#
# Гипотеза (Мазный с.196: "карта данных (80 символов) занесётся в массив
# из 14 слов ... символ перевод строки (код 012)"; iocont%: EOR = LOG 12,
# ISOSP = 149 пробелов + EOR = ровно 25 слов):
#   зона 0 = записи (рекорды) друг за другом, БЕЗ контрольных слов;
#   запись = текст карты в ISO 8-бит (6 символов на слово, старший байт
#            первым), признак конца записи - символ 012 ("перевод строки"),
#            хвост слова заполнен пробелами 040.
#   Пробел ISO = 040, цифры = 060..071, '+'=053, '-'=055, '.'=056 и т.д.
#
# Режимы длины записи (chars = длина текста карты с пробелами):
#   w13  - текст 72 симв. + EOR       -> 73 симв. -> 13 слов
#   w14  - текст 80 симв. + EOR       -> 81 симв. -> 14 слов (Мазный)
#   w25  - текст 149 симв. + EOR      -> 150 симв. -> 25 слов (ISOSP/RECORD(25))
#   var  - текст как есть + EOR       -> переменная длина
# Хвост зоны после карт: пустые записи (пробелы + EOR) той же длины.
#
# Использование: mk_tom45c.py <колода.b6> <файл тома> <режим>

import sys

EOR = 0o12
SP = 0o40

ISO = {' ': 0o40, '!': 0o41, '"': 0o42, '#': 0o23, '$': 0o44, '%': 0o45,
       '&': 0o46, "'": 0o47, '(': 0o50, ')': 0o51, '*': 0o52, '+': 0o53,
       ',': 0o54, '-': 0o55, '.': 0o56, '/': 0o57, ':': 0o72, ';': 0o73,
       '<': 0o74, '=': 0o75, '>': 0o76, '?': 0o77, '@': 0o60}
for i in range(10):
    ISO[chr(ord('0') + i)] = 0o60 + i
for i in range(26):
    c = chr(ord('A') + i)
    ISO[c] = 0o101 + i
    ISO[c.lower()] = 0o101 + i        # ГОСТ без регистра -> заглавные
CYR = 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
for i, ch in enumerate(CYR):
    ISO[ch] = 0o141 + i
    ISO[ch.lower()] = 0o141 + i


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
            cards.append(line.rstrip())
            if line.strip().lower().startswith('*end file'):
                break
    if not cards or not cards[-1].strip().upper().startswith('*END FILE'):
        cards.append('*end file')
    return cards


def enc_record(text, mode):
    """Карта -> список слов записи (ISO 8 бит, старший байт первым)."""
    t = text.rstrip().upper()
    if mode == 'w13':
        chars = [ISO.get(c, SP) for c in t.ljust(72)] + [EOR]
    elif mode == 'w14':
        chars = [ISO.get(c, SP) for c in t.ljust(80)] + [EOR]
    elif mode == 'w25':
        chars = [ISO.get(c, SP) for c in t.ljust(149)] + [EOR]
    elif mode == 'var':
        chars = [ISO.get(c, SP) for c in t] + [EOR]
    else:
        raise SystemExit('режим: w13|w14|w25|var')
    while len(chars) % 6:
        chars.append(SP)
    words = []
    for w in range(0, len(chars), 6):
        v = 0
        for c in chars[w:w + 6]:
            v = (v << 8) | (c & 0xFF)
        words.append(v)
    return words


def blank_record(mode):
    """Пустая запись (заполнитель хвоста зоны)."""
    if mode == 'w13':
        chars = [SP] * 72 + [EOR]
    elif mode == 'w14':
        chars = [SP] * 80 + [EOR]
    elif mode == 'w25':
        chars = [SP] * 149 + [EOR]
    else:
        chars = [SP] * 149 + [EOR]     # var -> пустая запись 25 слов
    words = []
    for w in range(0, len(chars), 6):
        v = 0
        for c in chars[w:w + 6]:
            v = (v << 8) | (c & 0xFF)
        words.append(v)
    return words


def main():
    deck, tom, mode = sys.argv[1], sys.argv[2], sys.argv[3]
    cards = read_data_cards(deck)
    print(f'карт данных: {len(cards)}; режим {mode}')
    for c in cards:
        print('  |' + c + '|')

    zone = [0] * 1024
    pos = 0
    blank = blank_record(mode)
    nb = len(blank)
    for c in cards:
        rec = enc_record(c, mode)
        assert pos + len(rec) <= 1024, 'не лезет'
        zone[pos:pos + len(rec)] = rec
        pos += len(rec)
    while pos + nb <= 1024:            # хвост зоны - пустые записи
        zone[pos:pos + nb] = blank
        pos += nb
    with open(tom, 'wb') as f:
        for w in zone:
            f.write(w.to_bytes(6, 'big'))
    print(f'записан {tom}: записей карт до слова {pos}, всего 6144 байта')
    print(f'  [0000] = {zone[0]:016o}')
    print(f'  [0001] = {zone[1]:016o}')


if __name__ == '__main__':
    main()
