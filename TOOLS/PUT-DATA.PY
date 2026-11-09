#!/usr/bin/env python3
# Подготовка тома данных задачи (МД 45) для пакетного эмулятора dispak.
# Карты данных упаковываются по 24 слова (5 ГОСТ-байтов на слово,
# бит чётности в разряде 7) - как элемент А3 входной очереди.
# Формат файла тома - "новая структура" dispak: 8 управляющих слов
# + 1024 слова данных на зону (uint64 LE, 48-битные значения).
import sys

# ГОСТ-10859: коды нужных символов (из gost10859.h)
GOST = {' ': 0o17, '0': 0o00, '1': 0o01, '2': 0o02, '3': 0o03,
        '4': 0o04, '5': 0o05, '6': 0o06, '7': 0o07, '8': 0o10,
        '9': 0o11, '+': 0o12, '-': 0o13, ',': 0o15, '.': 0o16,
        '/': 0o14, '=': 0o25, '(': 0o34, ')': 0o35, '*': 0o31}

def parity(b):
    b = (b ^ (b >> 4)) & 0xf
    b = (b ^ (b >> 2)) & 0x3
    b = (b ^ (b >> 1)) & 0x1
    return 1 - b  # 1 при чётном числе единиц

def card_words(line):
    """Карта текста -> 24 слова по 48 бит."""
    w = [0] * 24
    for i, ch in enumerate(line[:120]):
        c = GOST.get(ch)
        if c is None:
            raise SystemExit(f"нет кода ГОСТ для {ch!r}")
        w[i // 5] = ((w[i // 5] << 8) | (c | parity(c) << 7)) & ((1 << 48) - 1)
    n = len(line[:120])
    if n % 5:
        w[n // 5] = (w[n // 5] << (8 * (5 - n % 5))) & ((1 << 48) - 1)
    return w

def zone_file(words_per_zone, cards):
    """Сборка файла тома: зоны по 1024 слова, карты подряд с зоны 0."""
    allw = []
    for c in cards:
        allw += card_words(c)
    zones = []
    for z in range(0, max(1, (len(allw) + 1023) // 1024)):
        zw = allw[z * 1024:(z + 1) * 1024]
        zw = zw + [0] * (1024 - len(zw))
        zones.append(zw)
    out = b''
    for zw in zones:
        out += b''.join((0).to_bytes(8, 'little') for _ in range(8))
        out += b''.join(v.to_bytes(8, 'little') for v in zw)
    return out

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    lines = open(src, encoding='utf-8').read().splitlines()
    lines = [l for l in lines if l.strip()]
    data = zone_file(1024, lines)
    open(dst, 'wb').write(data)
    print(f'{dst}: {len(lines)} карт, {len(data)} байт')
