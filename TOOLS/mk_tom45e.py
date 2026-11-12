#!/usr/bin/env python3
# Шаг 2 (план А2): том 202 = входной поток ЛУН 45, формат ЛИСТА ДАННЫХ
# по контракту IOXXFMR/МОNRЕАД* (ANALIZ.md, Шаг 1-2).
# Вариант e8 (текущий): записи 25 слов = [ключ REC, conv=1] + 24 слова
# текста (карта 80 симв + EOR + добивка 0o40, conv=2); маркер [11201]
# на сл. 0o12 (conv=1); маркер [11200] - конец потока.
# Гипотеза e8: монread отличает служебные слова по БИТАМ КОНВОЛЮЦИИ
# (разряды 48-49: 1=команда, 2=данные), а не по содержанию.
# Использование: mk_tom45e.py <колода.b6> <файл тома> [вариант] [число зон]
import sys

SP = 0o40
EOR = 0o12
ZONE_OFFSET = 4
CONV_CMD = 1                          # бит конволюции "команда"
CONV_DATA = 2                         # бит конволюции "данные"
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
    """Запись e8: 25 слов = [ключ REC, conv=1] + 24 слова текста
    (карта 80 симв + EOR + добивка 0o40, conv=2)."""
    chars = [ISO.get(c, SP) for c in text.upper()][:80]
    chars.append(EOR)
    chars += [SP] * (144 - len(chars))
    words = []
    for w in range(0, 144, 6):
        v = 0
        for c in chars[w:w + 6]:
            v = (v << 8) | (c & 0xFF)
        words.append(v)
    return [(REC_KEY, CONV_DATA)] + [(w, CONV_CMD) for w in words]


def main():
    deck, tom = sys.argv[1], sys.argv[2]
    variant = sys.argv[3] if len(sys.argv) > 3 else 'e8'
    nzones = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    cards = read_data_cards(deck)
    print(f'карт данных: {len(cards)}; вариант {variant}')
    zone = [0] * 1024
    conv = [CONV_DATA] * 1024
    pos = 0
    if variant in ('e1', 'e3', 'e8'):
        if variant == 'e3':
            zone[0] = 0o2104140
        pos = 0o12                       # сл. 0..0o11 - заголовок
        zone[pos] = MARK_CONT            # "лист продолжается"
        conv[pos] = CONV_DATA if variant == 'e8' else CONV_DATA
        pos += 1
    for c in cards:
        rec = enc_rec(c)
        if pos + len(rec) > 1024:
            break
        for w, cv in rec:
            zone[pos] = w
            conv[pos] = cv
            pos += 1
    if pos < 1024:
        zone[pos] = MARK_END             # конец потока
        conv[pos] = CONV_DATA if variant == 'e8' else CONV_DATA
        pos += 1
    while pos + 25 <= 1024:              # хвост: пустые записи
        for w, cv in enc_rec(''):
            zone[pos] = w
            conv[pos] = cv
            pos += 1

    ZT = 64 + 1024 * 8
    with open(tom, 'wb') as f:
        for z in range(ZONE_OFFSET + nzones):
            if z == ZONE_OFFSET:
                f.write((0).to_bytes(64, 'big'))
                for i in range(1024):
                    v = zone[i] | (conv[i] << 48)
                    f.write(v.to_bytes(8, 'little'))
            else:
                f.write((0).to_bytes(ZT, 'big'))
    print(f'записан {tom}: {ZONE_OFFSET + nzones} zone_t, карты до слова {pos}')
    print(f'  [0000] = {zone[0]:016o} conv={conv[0]}')
    print(f'  [0012] = {zone[0o12]:016o} conv={conv[0o12]}')
    print(f'  [0013] = {zone[0o13]:016o} conv={conv[0o13]}')


if __name__ == '__main__':
    main()
