#!/usr/bin/env python3
# Шаг 2/3б (план А2): том 202 = входной поток ЛУН 45, формат ЛИСТА ДАННЫХ
# по контракту IOXXFMR/МОNRЕАД* (ANALIZ.md, Шаг 1, п.5):
#   слова 0..0o11 - заголовок листа (нули),
#   слово 0o12 = [11201] (0o6000...0000) - "лист продолжается" (статус 0),
#   далее записи: "REC"+80 симв+EOR = 84 байта = 14 слов (ISO 8 бит,
#   старший байт первым, добивка 0o40),
#   после последней записи - [11200] (0o3000...0000) = конец данных,
#   хвост зоны - пустые записи-пробелы.
# Варианты (argv[4]): e1 (маркер [11201] на сл.0o12), e2 (без заголовка -
# запись с сл.0, маркер [11201] на сл.0o12 = внутри 1-й записи), e3
# (заголовок 0o2104140/0 сл.0-1 + маркер [11201] на сл.0o12).
#
# Использование: mk_tom45e.py <колода.b6> <файл тома> [вариант] [число зон]
import sys

SP = 0o40
EOR = 0o12
ZONE_OFFSET = 4
CONV_DATA = 2
MARK_CONT = 0o6000000000000000   # [11201]: продолжить лист
MARK_END  = 0o3000000000000000   # [11200]: конец потока

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


REC_KEY = 0o2444250310020040        # ISO "REC   " - ключ записи (4001/з0o504 сл.0o1554)

def enc_rec(text):
    """Запись e6: 25 слов = 150 байт ЧИСТОГО ТЕКСТА
    (карта + EOR + добивка 0o40), без ключа."""
    chars = [ISO.get(c, SP) for c in text.upper()][:80]
    chars += [SP] * (149 - len(chars))
    chars.append(EOR)
    words = []
    for w in range(0, 150, 6):
        v = 0
        for c in chars[w:w + 6]:
            v = (v << 8) | (c & 0xFF)
        words.append(v)
    return words                         # 25 слов


def main():
    deck, tom = sys.argv[1], sys.argv[2]
    variant = sys.argv[3] if len(sys.argv) > 3 else 'e1'
    nzones = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    cards = read_data_cards(deck)
    print(f'карт данных: {len(cards)}; вариант {variant}')
    zone = [0] * 1024
    pos = 0
    if variant in ('e1', 'e3'):
        if variant == 'e3':
            zone[0] = 0o2104140
        pos = 0o12                       # сл. 0..0o11 - заголовок
        zone[pos] = MARK_CONT            # "лист продолжается"
        pos += 1
    for c in cards:
        rec = enc_rec(c)
        if variant == 'e2' and pos == 0:
            zone[pos:pos + len(rec)] = rec
            pos += len(rec)
            continue
        if pos + len(rec) > 1024:
            break
        zone[pos:pos + len(rec)] = rec
        pos += len(rec)
    if pos < 1024:
        zone[pos] = MARK_END             # конец потока
        pos += 1
    while pos + 14 <= 1024:              # хвост: пустые записи
        blank = enc_rec('')
        zone[pos:pos + 14] = blank
        pos += 14

    ZT = 64 + 1024 * 8
    with open(tom, 'wb') as f:
        for z in range(ZONE_OFFSET + nzones):
            if z == ZONE_OFFSET:
                f.write((0).to_bytes(64, 'big'))
                for w in zone:
                    f.write(((CONV_DATA << 48) | w).to_bytes(8, 'little'))
            else:
                f.write((0).to_bytes(ZT, 'big'))
    print(f'записан {tom}: {ZONE_OFFSET + nzones} zone_t, карты до слова {pos}')
    print(f'  [0000] = {zone[0]:016o}')
    print(f'  [0012] = {zone[0o12]:016o}')
    print(f'  [0013] = {zone[0o13]:016o}')


if __name__ == '__main__':
    main()
