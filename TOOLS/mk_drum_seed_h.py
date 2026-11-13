#!/usr/bin/env python3
# Шаг 6 (план А2, штатный путь): подсадка ЛИСТ-КОНВЕРТА в барабан-спул
# dispak через BESM6_DRUM_SEED (патч Шага 6). Имитирует то, что штатная
# МОНА-80 кладёт в спул: лист с заголовком и маркером на сл.0o12
# (IOXXFMR-контракт; ETAP1 п. 10.4). Том 202 НЕ используется.
#
# Формат seed-файла: Physical (zone_t), 8256 байт на зону;
#   зона N seed-файла = зона N барабанного файла drumh:
#   тракт t барабана d = зона (t + d*0o40) файла (дес. t + d*32).
# По умолчанию: барабан 21 (спул МОНЫ), тракт 2 (там лежит поток задачи).
#
# Варианты раскладки конверта (по результатам e/f-серии 12.11):
#   h-серия (13.11): заголовок 12 слов (0o0-0o13), тело с 0o14 (dec 12)
#       - запись начинается со сл.0o14 (печать 'П' в s6-c = сл.0o14 заголовка)
#   a - тёплый старт e5/f2: заголовок 4023/0o554 verbatim, сл.0o12=[11200],
#       записи по 25 слов: [REC-ключ][24 слова ISO-текста (149 симв.+EOR)];
#       *END FILE - такая же запись; конец тела - маркер [11200].
#   b - как a, без REC-ключей (f1-baseline).
#   c - как a, но после записи *END FILE добавляется слово 0o7760000000000012
#       (слово конца потока из сырого спула МОНЫ).
#   d - тело = verbatim слова спула МОНЫ (ISO, перем. длина, EOR 0o12,
#       конец 0o7760000000000012) - гипотеза "монread% читает сырой спул
#       в конвертной обёртке".
#   e - как a, но текст ГОСТ-6БИТ (8 симв./слово, записи 26 слов) -
#       гипотеза Шага 5.
#
# Использование: mk_drum_seed.py <колода.b6> <seed-файл> <вариант>
#                 [барабан(восьм., умолч. 21)] [тракт(восьм., умолч. 2)]
import sys

SP = 0o40
EOR = 0o12
CONV_DATA = 2
CONV_CMD = 1
MARK_END  = 0o3000000000000000   # [11200]
MARK_CONT = 0o6000000000000000   # [11201]
KEY_REC   = 0o200000000200001    # служебное слово записи (IOCONT*)
WORD_END  = 0o7760000000000012   # конец потока в спуле МОНЫ

# аутентичный заголовок (том 4023/з0o554): сл.0 + маркеры-веса VGR
HEADER = [0o0000000000022015,
          0o6400000000000000, 0o6000000000000000, 0o5400000000000000,
          0o5000000000000000, 0o4400000000000000, 0o4000000000000000,
          0o1400000000000000, 0o2000000000000000, 0o2400000000000000,
          0o3000000000000000, 0o3400000000000000]

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

GOST = {0o00: '0', 0o01: '1', 0o02: '2', 0o03: '3', 0o04: '4', 0o05: '5',
        0o06: '6', 0o07: '7', 0o10: '8', 0o11: '9', 0o12: '+', 0o13: '-',
        0o14: '/', 0o15: ',', 0o16: '.', 0o17: ' ', 0o22: '(', 0o23: ')',
        0o25: '=', 0o31: '*', 0o35: '<', 0o36: '>', 0o37: ':',
        0o40: 'А', 0o41: 'Б', 0o42: 'В', 0o43: 'Г', 0o44: 'Д', 0o45: 'Е',
        0o46: 'Ж', 0o47: 'З', 0o50: 'И', 0o51: 'Й', 0o52: 'К', 0o53: 'Л',
        0o54: 'М', 0o55: 'Н', 0o56: 'О', 0o57: 'П', 0o60: 'Р', 0o61: 'С',
        0o62: 'Т', 0o63: 'У', 0o64: 'Ф', 0o65: 'Х', 0o66: 'Ц', 0o67: 'Ч',
        0o70: 'Ш', 0o71: 'Щ', 0o72: 'Ы', 0o73: 'Ь', 0o74: 'Э', 0o75: 'Ю',
        0o76: 'Я', 0o77: 'D', 0o100: 'F', 0o101: 'G', 0o102: 'I',
        0o103: 'J', 0o104: 'L'}
GOST_R = {v: k for k, v in GOST.items()}


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


def pack(chars, bits=8, pad=SP):
    """Список кодов -> слова по 48/bits символов."""
    while len(chars) % (48 // bits):
        chars.append(pad)
    words = []
    for w in range(0, len(chars), 48 // bits):
        v = 0
        for c in chars[w:w + 48 // bits]:
            v = (v << bits) | (c & ((1 << bits) - 1))
        words.append(v)
    return words


WORD_EOR = 0o1002004010020012    # слово конца карты: 5 пробелов + 0o12
                                  # (эталон [М1+211₈], снят из core-pc.bin
                                  #  в момент печати ошибки IOCONT*, Шаг 6)

def enc_iso_words(text, width=72):
    """Карта -> 13 слов: 12 слов ISO-текста (72 колонки, пробелы) +
    слово EOR (5 пробелов + 0o12) - формат MONCARD* (Шаг 6)."""
    chars = [ISO.get(c, SP) for c in text.upper().ljust(width)]
    return pack(chars, 8, ISO[' ']) + [WORD_EOR]


def enc_gost_words(text, width=72):
    """Карта -> 10 слов: 9 слов ГОСТ-6БИТ (72 колонки) + слово EOR."""
    cs = [GOST_R.get(c, GOST_R[' ']) for c in text.upper().ljust(width)]
    return pack(cs, 6, GOST_R[' ']) + [WORD_EOR]

def enc13(text):
    """Карта -> 13 слов ISO (78 колонок, пробелы)."""
    chars = [ISO.get(c, SP) for c in text.upper().ljust(78)]
    return pack(chars, 8, ISO[' '])


def enc_iso_var(text):
    """Карта переменной длины (как в спуле МОНЫ): ISO, EOR в конце."""
    chars = [ISO.get(c, SP) for c in text.upper()] + [EOR]
    return pack(chars, 8, ISO[' '])


def spool_stream_words(deck_path):
    """Слова сырого спула МОНЫ: *EXECUTE + карты данных + *END FILE + конец."""
    ws = []
    ws += enc_iso_var('*execute')
    for c in read_data_cards(deck_path):
        ws += enc_iso_var(c)
    ws.append(WORD_END)
    return ws


def build_zone(deck_path, variant, cont=True):
    """Зона конверта. cont=True -> маркер [11201] (лист продолжается);
    cont=False -> [11200] (конец листа, пустое тело)."""
    zone = [0] * 1024
    conv = [0] * 1024
    for i, w in enumerate(HEADER):
        zone[i] = w
        conv[i] = CONV_CMD
    zone[0o12] = MARK_CONT if cont else MARK_END
    conv[0o12] = CONV_CMD
    pos = 0o14
    if not cont:
        return zone, conv, pos
    if variant == 'd':
        for w in spool_stream_words(deck_path):
            zone[pos] = w; conv[pos] = CONV_DATA; pos += 1
        zone[pos] = MARK_END; conv[pos] = CONV_DATA; pos += 1
        return zone, conv, pos

    cards = read_data_cards(deck_path)
    data_cards = [c for c in cards if not c.strip().upper().startswith('*END FILE')]
    gost = (variant == 'e')
    enc = enc_gost_words if gost else enc_iso_words
    # g1: [ключ][карта 12 слов][11 слов пробелов][EOR-слово] = 25 слов
    # g2: [карта 13 слов][EOR-слово] = 14 слов (без ключа)
    # g3: [ключ][карта 13 слов][EOR-слово][заполнители до 25] = 25 слов
    rlen = 25 if variant in ('a', 'g1', 'g3') else 14 if variant == 'g2' else 13
    key = variant in ('a', 'g1', 'g3', 'e')

    def put_record(text):
        nonlocal pos
        if variant == 'g1':
            zone[pos] = KEY_REC; conv[pos] = CONV_DATA; pos += 1
            for w in enc(text):        # 12 слов текста (72 колонки)
                zone[pos] = w; conv[pos] = CONV_DATA; pos += 1
            for _ in range(11):        # 11 слов пробелов
                zone[pos] = 0o404040404040; conv[pos] = CONV_DATA; pos += 1
            zone[pos] = WORD_EOR; conv[pos] = CONV_DATA; pos += 1
            return
        if variant == 'g2':
            for w in enc13(text):      # 13 слов текста (78 колонок)
                zone[pos] = w; conv[pos] = CONV_DATA; pos += 1
            zone[pos] = WORD_EOR; conv[pos] = CONV_DATA; pos += 1
            return
        if variant == 'g3':
            zone[pos] = KEY_REC; conv[pos] = CONV_DATA; pos += 1
            for w in enc13(text):      # 13 слов текста
                zone[pos] = w; conv[pos] = CONV_DATA; pos += 1
            zone[pos] = WORD_EOR; conv[pos] = CONV_DATA; pos += 1
            while (pos - 0o15) % 25:   # добить до границы 25 слов
                zone[pos] = 0o404040404040; conv[pos] = CONV_DATA; pos += 1
            return
        blen = rlen - (1 if key else 0)
        body = (enc(text) + [0] * 32)[:blen]
        if key:
            zone[pos] = KEY_REC; conv[pos] = CONV_DATA; pos += 1
        for w in body:
            zone[pos] = w; conv[pos] = CONV_DATA; pos += 1

    for c in data_cards:
        put_record(c)
    put_record('*end file')
    if variant == 'c':
        zone[pos] = WORD_END; conv[pos] = CONV_DATA; pos += 1
    zone[pos] = MARK_END; conv[pos] = CONV_DATA; pos += 1
    return zone, conv, pos


def main():
    deck, out, variant = sys.argv[1], sys.argv[2], sys.argv[3]
    drum = int(sys.argv[4], 8) if len(sys.argv) > 4 else 0o21
    tract = int(sys.argv[5], 8) if len(sys.argv) > 5 else 2
    # seed-запись k = тракт (tract+k): [0] - данные [11201], [1] - конец [11200]
    recs = [build_zone(deck, variant, cont=True),
            build_zone(deck, variant, cont=False)]
    # запись seed-файла = формат disk_writei: 1024 слов x 6 байт (BE) +
    # 1024 байт конволюции; запись k подсаживается на тракт (tract+k)
    with open(out, 'wb') as f:
        for k, (zone, conv, pos) in enumerate(recs):
            for w in zone:
                f.write(w.to_bytes(6, 'big'))
            for c in conv:
                f.write(bytes([c]))
    print(f'вариант {variant}: конверт в барабане {oct(drum)} тракты '
          f'{oct(tract)}-{oct(tract+1)} (данные [11201]@0o12, конец [11200]@0o12), '
          f'тело до слова {oct(recs[0][2])}')
    for w in (0, 0o12, 0o15):
        print(f'  [{w:03o}] = {recs[0][0][w]:016o}')


if __name__ == '__main__':
    main()
