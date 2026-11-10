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
#   w26  - w14 + маркер [11200] 3000..0000 после последней записи
#   w27  - w14 + маркер [11201] 6000..0000 после последней записи
#   w28  - w14 + оба маркера (3000..., затем 6000...)
#   w29  - ключ "REC" (3 байта) + 80 симв. + EOR = 84 байта = 14 слов
#          (формат записи листа МОНА-80: ключи REC/ADD/EOF/END/BSP/SEF/RWN
#           из констант [11202..11210], парсер 10627-10633, журнал п.8.13)
#          + маркер [11200] после последней записи, хвост - пробелы
#   w30  - как w29, но маркеры 3000... И 6000...
#   w31  - w29 + лидер-маркер 3000...0000 В НАЧАЛЕ зоны (проверка 10633
#          смотрит ПЕРВОЕ слово листа: при обычном слове и [И1+17]=0
#          путь 10703-10724 даёт ошибку 0021, трасса w29, п.8.15)
#   w32  - как w31, но лидер 6000...0000 ([11201])
#   w34  - заголовок 10 слов (нули) + маркер 3000... в слове 0o12 (10 dec)
#          + записи REC + хвост: парсер читает [76000+И4], И4=12(восм),
#          т.е. слово 10 dec листа (xta 0000(4) при М0=76000, п.8.15)
#   w35  - как w34, но маркер 6000...0000
# Маркеры найдены дизассемблированием пост-обработки 10633-10641
# (сверка слова листа с [11200]/[11201], журнал п. 8.12-8.13).
# Хвост зоны после карт: пустые записи (пробелы + EOR) той же длины.

MARK_END_SHEET = 0o3000000000000000     # [11200]
MARK_END_REC  = 0o6000000000000000      # [11201]
SP6 = 0o1002004010020040                # [11216] - слово из 6 пробелов
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
    base = {'w26': 'w14', 'w27': 'w14', 'w28': 'w14',
            'w29': 'rec', 'w30': 'rec', 'w31': 'rec', 'w32': 'rec',
            'w34': 'rec', 'w35': 'rec'}.get(mode, mode)
    if base == 'w13':
        chars = [ISO.get(c, SP) for c in t.ljust(72)] + [EOR]
    elif base == 'w14':
        chars = [ISO.get(c, SP) for c in t.ljust(80)] + [EOR]
    elif base == 'rec':
        # ключ "REC" + 80 симв. карты + EOR = 84 байта = 14 слов
        chars = [ISO['R'], ISO['E'], ISO['C']] + \
                [ISO.get(c, SP) for c in t.ljust(80)] + [EOR]
    elif mode == 'w25':
        chars = [ISO.get(c, SP) for c in t.ljust(149)] + [EOR]
    elif mode == 'var':
        chars = [ISO.get(c, SP) for c in t] + [EOR]
    else:
        raise SystemExit('режим: w13|w14|w25|var|w26..w30')
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
    mode = {'w26': 'w14', 'w27': 'w14', 'w28': 'w14'}.get(mode, mode)
    if mode in ('w29', 'w30', 'w31', 'w32', 'w34', 'w35'):
        return [SP6]              # хвост - слова из 6 пробелов ([11216])
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
    if mode == 'w31':                       # лидер-маркер начала листа
        zone[pos] = MARK_END_SHEET; pos += 1
        print(f'  лидер {MARK_END_SHEET:016o} в слово {pos-1:05o}')
    if mode == 'w32':
        zone[pos] = MARK_END_REC; pos += 1
        print(f'  лидер {MARK_END_REC:016o} в слово {pos-1:05o}')
    if mode in ('w34', 'w35'):              # маркер после 10-словного заголовка
        pos = 0o12                          # слово 10 dec = [76000+И4]
        zone[pos] = MARK_END_SHEET if mode == 'w34' else MARK_END_REC
        print(f'  маркер {zone[pos]:016o} в слово {pos:05o} (заголовок 0-9 нули)')
        pos += 1
    blank = blank_record(mode)
    nb = len(blank)
    for c in cards:
        rec = enc_record(c, mode)
        assert pos + len(rec) <= 1024, 'не лезет'
        zone[pos:pos + len(rec)] = rec
        pos += len(rec)
    if mode in ('w26', 'w27', 'w28', 'w29', 'w30', 'w31', 'w32', 'w34', 'w35'):  # метки конца
        marks = {'w26': [MARK_END_SHEET],
                 'w27': [MARK_END_REC],
                 'w28': [MARK_END_SHEET, MARK_END_REC],
                 'w29': [MARK_END_SHEET],
                 'w30': [MARK_END_SHEET, MARK_END_REC],
                 'w31': [MARK_END_SHEET],
                 'w32': [MARK_END_SHEET],
                 'w34': [MARK_END_SHEET],
                 'w35': [MARK_END_SHEET]}[mode]
        for m in marks:
            zone[pos] = m
            print(f'  маркер {m:016o} в слово {pos:05o}')
            pos += 1
    while pos + nb <= 1024:            # хвост зоны - пустые записи
        zone[pos:pos + nb] = blank
        pos += nb
    write_tom2(tom, zone)
    print(f'записан {tom}: записей карт до слова {pos}, формат new-structure')
    print(f'  [0000] = {zone[0]:016o}')
    print(f'  [0001] = {zone[1]:016o}')


def write_tom2(tom, zone):
    """Том в формате disk_readi2 (new structure, ЖУРНАЛ п. 8.14):

        файл = зоны zone_t по 6208 байт: 64 байта контрольных слов (нули)
               + 1024 слова по 6 байт, разряды 48-49 = 01 (convol=0);
        зона 0 ЛУН = зона №4 файла (ZONE_OFFSET = 4, disk.c);
        зоны 0-3 файла - резерв (паспорт), держим нулевыми.

    Сырой файл 6144 байта dispak читал как readi2 с зоны 4 - за концом
    файла - и тихо подсовывал заполнитель "====..." (disk_formcodei),
    что и давало "ИСПОРЧЕН РЕКОРД" при любом содержимом зоны.
    """
    import struct
    NTOT = 240          # всего зон в файле (запас для спула МОНА-80)
    # zone_t читается dispak как native uint64 (LE на x86) - п.8.15
    blank = b''.join((1 << 48).to_bytes(8, 'little') for _ in range(1024))
    with open(tom, 'wb') as f:
        for zn in range(NTOT):
            f.write(b'\0' * 64)                 # z_cwords[8] (uint64 LE)
            if zn == 4:
                for w in zone:
                    f.write(((1 << 48) | w).to_bytes(8, 'little'))
            else:
                f.write(blank)


if __name__ == '__main__':
    main()
