#!/usr/bin/env python3
# Этап 1 (А2, эксперимент v3): том 202 = входной поток ЛУН 45 в НОВОМ
# формате томов dispak (disk_readi2, "Physical"): файл = массив zone_t,
# zone_t = 8 контрольных слов (64 байта) + 1024 слова данных (6144 байт).
# ЗОНА_OFFSET = 4: логическая зона 0 тома = ФИЗИЧЕСКАЯ зона 4 файла
# (зоны 0-3 служебные; у собранного штатно тома 2099 они нулевые).
# Каждое слово данных снабжается битом конволюции: 2 = данные, 1 = команда.
# Содержимое зоны 0: записи карт в формате А1 (МОNRЕАД* Монитора-80):
#   текст карты в ISO 8-бит (6 симв. на слово, старший байт первым),
#   признак конца записи - символ 012 ("перевод строки"), добивка 040.
# Режимы: w13 (72+1 симв.), w14 (80+1), w25 (149+1), var.
#
# Использование: mk_tom45d.py <колода.b6> <файл тома> <режим> [число зон]

import sys

EOR = 0o12
SP = 0o40
ZONE_OFFSET = 4      # логическая зона 0 = физическая зона 4
CONV_DATA = 2        # бит конволюции "данные"

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


MARK_END = 0o3000000000000000     # метка конца записи ([11200] IOXXFMR)
MARK_EOE = 0o6000000000000000     # метка [11201]

def enc_record(text, mode):
    """Карта -> список слов записи (ISO 8 бит, старший байт первым)."""
    t = text.rstrip().upper()
    if mode == 'w10m':
        # 10 слов текста (60 симв.) + слово 010 = метка конца записи
        chars = [ISO.get(c, SP) for c in t.ljust(60)]
        words = []
        for w in range(0, 60, 6):
            v = 0
            for c in chars[w:w + 6]:
                v = (v << 8) | (c & 0xFF)
            words.append(v)
        words.append(MARK_END)
        return words
    if mode == 'w13':
        chars = [ISO.get(c, SP) for c in t.ljust(72)] + [EOR]
    elif mode == 'w14':
        chars = [ISO.get(c, SP) for c in t.ljust(80)] + [EOR]
    elif mode == 'w25':
        chars = [ISO.get(c, SP) for c in t.ljust(149)] + [EOR]
    elif mode == 'var':
        chars = [ISO.get(c, SP) for c in t] + [EOR]
    else:
        raise SystemExit('режим: w10m|w13|w14|w25|var')
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
    if mode == 'w10m':
        return [0o404040404040] * 10 + [MARK_END]
    n = {'w13': 72, 'w14': 80, 'w25': 149}.get(mode, 149)
    chars = [SP] * n + [EOR]
    words = []
    for w in range(0, len(chars), 6):
        v = 0
        for c in chars[w:w + 6]:
            v = (v << 8) | (c & 0xFF)
        words.append(v)
    return words


def main():
    deck, tom, mode = sys.argv[1], sys.argv[2], sys.argv[3]
    nzones = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    cards = read_data_cards(deck)
    print(f'карт данных: {len(cards)}; режим {mode}')
    for c in cards:
        print('  |' + c + '|')

    zone = [0] * 1024
    pos = 0
    blank = blank_record(mode)
    nb = len(blank)
    if mode == 'w10m':
        # каждая запись: 10 слов текста + метка конца записи [11200];
        # колода данных заканчивается записью *END FILE -> метка [11201]
        for c in cards:
            rec = enc_record(c, mode)
            assert pos + len(rec) <= 1024, 'не лезет'
            zone[pos:pos + len(rec)] = rec
            pos += len(rec)
        # вместо текста *END FILE - метка конца потока [11201]
        while pos + 11 <= 1024:        # хвост: пустые записи с меткой
            zone[pos:pos + 10] = [0o404040404040] * 10
            zone[pos + 10] = MARK_EOE
            pos += 11
    else:
        for c in cards:
            rec = enc_record(c, mode)
            assert pos + len(rec) <= 1024, 'не лезет'
            zone[pos:pos + len(rec)] = rec
            pos += len(rec)
        while pos + nb <= 1024:            # хвост зоны - пустые записи
            zone[pos:pos + nb] = blank
            pos += nb

    ZT = 64 + 1024 * 8                 # sizeof(zone_t) = 8256 байт
    with open(tom, 'wb') as f:
        for z in range(ZONE_OFFSET + nzones):
            if z == ZONE_OFFSET:
                f.write((0).to_bytes(64, 'big'))        # cwords = 0 (как у 2099)
                for w in zone:
                    f.write(((CONV_DATA << 48) | w).to_bytes(8, 'little'))
            else:
                f.write((0).to_bytes(ZT, 'big'))        # пустая zone_t
    print(f'записан {tom}: {ZONE_OFFSET + nzones} zone_t '
          f'({(ZONE_OFFSET + nzones) * ZT} байт, sizeof(zone_t)=8256), '
          f'карты в физ.зоне {ZONE_OFFSET} до слова {pos}')
    print(f'  [0000] = {zone[0]:016o}')
    print(f'  [0001] = {zone[1]:016o}')


if __name__ == '__main__':
    main()
