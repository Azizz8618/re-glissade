#!/usr/bin/env python3
# Этап 1 (А1/А2): формирование тома 202 (входной поток ЛУН 45) в формате
# записи МОNRЕАД* Монитора-80.
# Зона = 1024 слова:
#   000-007: 0 (служебные, не проверяются)
#   010-017: контрольные слова зоны (по put_check_words dispak):
#     [010] = 0 (unit id + date)
#     [011] = user id (0)
#     [012] = (том<<6) в левой половине, том в правой
#     [013] = 070707 (ключ) | ((2*зона+010)<<12 | (2*зона+010))
#     [015] = копия последнего слова зоны
#     [016] = как [013]
#     [017] = 48-бит сумма всех 1024 слов
#   020..1023: записи карт по 12 слов x 8 симв. ГОСТ 10859 (96 симв.),
#              ровно 84 карты на зону.
# Использование: mk_tom45b.py <колода.b6> <файл тома 202> [assigned_vol] [phys_vol]

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
GOST.setdefault('#', 0o20)
GOST.setdefault('H', 0o105)   # H -> N (по таблице dispak)

def enc_card(text):
    s = (text + ' ' * 96)[:96]
    words = []
    for w in range(12):
        v = 0
        for c in s[w * 8:(w + 1) * 8]:
            v = (v << 6) | GOST.get(c, 0o17)
        words.append(v)
    return words

def checksum(words):
    s = 0
    for w in words:
        s = (s + w) & ((1 << 48) - 1)
    return s

def main():
    deck, tom = sys.argv[1], sys.argv[2]
    assigned = int(sys.argv[3], 8) if len(sys.argv) > 3 else 0o45
    phys = int(sys.argv[4]) if len(sys.argv) > 4 else 202
    zone_no = 0
    cards = read_data_cards(deck)
    print(f'карт данных: {len(cards)} (assigned={oct(assigned)}, phys={phys})')

    data = []
    for c in cards:
        data.extend(enc_card(c))
    assert len(data) <= (1024 - 0o20), 'не лезет в одну зону'

    w12 = ((phys << 6) & 0xFFFFFF) << 24 | (phys & 0xFFFFFF)
    half = (2 * zone_no + 0o10)
    w13 = (0o70707 << 24) | ((half << 12) & 0xFFFFFF) | (half & 0xFFF)

    zone = [0] * 1024
    zone[0o12] = w12
    zone[0o13] = w13
    zone[0o16] = w13
    for i, w in enumerate(data):
        zone[0o20 + i] = w
    zone[0o15] = zone[0o1777]
    zone[0o17] = checksum(zone)
    assert len(zone) == 1024
    with open(tom, 'wb') as f:
        for w in zone:
            f.write(w.to_bytes(6, 'big'))
    print('записан', tom, '= 6144 байт')
    print(f'  [012] = {zone[0o12]:016o}')
    print(f'  [013] = {zone[0o13]:016o}')
    print(f'  [017] = {zone[0o17]:016o}')
    print(f'  [020] = {zone[0o20]:016o} (первое слово карты 1)')

if __name__ == '__main__':
    main()
