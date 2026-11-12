#!/usr/bin/env python3
# Шаг 2з (план А2): том 202 = ЛИСТ-КОНВЕРТ по аутентичному образцу
# тома 4023/з0o554 (член-лист МОNRЕАД*-семьи):
#   сл.0      = 0o22015 (заголовок листа, conv=1)
#   сл.1..0o14= маркеры-веса 0o6400/6000/5400/5000/4400/4000/1400/
#               2000/2400/3000/3400/4000/0000 (conv=1), сл.0o12 = [11200]
#   сл.0o14+  = тело: карты в ISO-8бит, 6 симв/слово, EOR 0x0A (conv=2)
# Варианты: f1 - сл.0o12 = [11200] (как в образце);
#           f2 - сл.0o12 = [11201] (продолжить).
# Использование: mk_tom45f.py <колода.b6> <файл тома> [f1|f2] [число зон]
import sys

SP = 0o40
EOR = 0o12
ZONE_OFFSET = 4
CONV_CMD = 1
CONV_DATA = 2
MARK_END  = 0o3000000000000000   # [11200]
MARK_CONT = 0o6000000000000000   # [11201]

# аутентичный заголовок (том 4023/з0o554, сл.0..0o14, conv=1)
HEADER = [0o0000000000022015,
          0o6400000000000000, 0o6000000000000000, 0o5400000000000000,
          0o5000000000000000, 0o4400000000000000, 0o4000000000000000,
          0o1400000000000000, 0o2000000000000000, 0o2400000000000000,
          0o3000000000000000, 0o3400000000000000, 0o4000000000000000,
          0o4000000000000000]
HDR_MARK_POS = 0o12              # сл.0o12 = маркер в заголовке
BODY_POS = int(sys.argv[5]) if len(sys.argv) > 5 else 0o15  # смещение тела
ZERO_LAST_WEIGHT = len(sys.argv) > 6

ISO = {' ': 0o40, '!': 0o41, '"': 0o42, '#': 0o23, '$': 0o44, '%': 0o45,
       '&': 0o46, "'": 0o47, '(': 0o50, ')': 0o51, '*': 0o52, '+': 0o53,
       ',': 0o54, '-': 0o55, '.': 0o56, '/': 0o57, ':': 0o72, ';': 0o73,
       '<': 0o74, '=': 0o75, '>': 0o76, '?': 0o77, '@': 0o60}
for i in range(10):
    ISO[chr(ord('0') + i)] = 0o60 + i
for i in range(26):
    c = chr(ord('A') + i)
    ISO[c] = 0o101 + i
    ISO[c.lower()] = 0o101 + i
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


def enc_card(text):
    """Карта: ISO 8 бит, 6 симв/слово, EOR 0x0A в конце, добивка 0o40."""
    chars = [ISO.get(c, SP) for c in text.upper()]
    chars.append(EOR)
    while len(chars) % 6:
        chars.append(SP)
    words = []
    for w in range(0, len(chars), 6):
        v = 0
        for c in chars[w:w + 6]:
            v = (v << 8) | (c & 0xFF)
        words.append(v)
    return words


def main():
    deck, tom = sys.argv[1], sys.argv[2]
    variant = sys.argv[3] if len(sys.argv) > 3 else 'f1'
    nzones = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    cards = read_data_cards(deck)
    print(f'карт данных: {len(cards)}; вариант {variant}')
    zone = [0] * 1024
    conv = [CONV_CMD] * 1024
    # заголовок verbatim
    for i, w in enumerate(HEADER):
        zone[i] = w
        conv[i] = CONV_CMD
    zone[HDR_MARK_POS] = MARK_END if variant == 'f1' else MARK_CONT
    if ZERO_LAST_WEIGHT:
        zone[0o14] = 0
    pos = BODY_POS                    # тело после заголовка
    # тело: карты
    sep = MARK_END if variant == 'f5' else None
    KEY_REC = 0o200000000200001    # ключ записи (IOCONT* [20661])
    for c in cards:
        rec = enc_card(c)
        if pos + len(rec) + 2 > 1024:
            break
        if variant == 'f7':
            zone[pos] = KEY_REC; conv[pos] = CONV_DATA; pos += 1
        for w in rec:
            zone[pos] = w
            conv[pos] = CONV_DATA
            pos += 1
        if sep is not None and pos < 1024:
            zone[pos] = sep            # маркер после каждой карты
            conv[pos] = CONV_DATA
            pos += 1
    if variant == 'f6' and pos < 1024:
        zone[pos] = 0o7760000000000012 # слово конца записи (iocont%)
        conv[pos] = CONV_DATA
        pos += 1
    if pos < 1024 and sep is None:
        zone[pos] = MARK_END           # конец потока
        conv[pos] = CONV_DATA
        pos += 1

    ZT = 64 + 1024 * 8
    with open(tom, 'wb') as f:
        for z in range(ZONE_OFFSET + nzones):
            if z == ZONE_OFFSET:
                f.write((0).to_bytes(64, 'big'))
                for i in range(1024):
                    f.write(((conv[i] << 48) | zone[i]).to_bytes(8, 'little'))
            else:
                f.write((0).to_bytes(ZT, 'big'))
    print(f'записан {tom}: {ZONE_OFFSET + nzones} zone_t, тело до слова {pos}')
    print(f'  [0000] = {zone[0]:016o} conv={conv[0]}')
    print(f'  [0012] = {zone[0o12]:016o} conv={conv[0o12]}')


if __name__ == '__main__':
    main()
