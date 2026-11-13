#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Поиск ГОСТ-6БИТ строки в дампе ядра (core-pc.bin, 65536 слов по 6 байт).
Слово = 8 символов по 6 бит (ГОСТ 10859), лексикографически слева направо.
Плюс дизассемблерная подсказка: кто ссылается на найденные адреса (uicore).
Использование: find_gost_str.py <core-pc.bin> <текст> [core-uic.bin]
"""
import sys

GOST_CYR = {
    'А': 0o40, 'Б': 0o41, 'В': 0o42, 'Г': 0o43, 'Д': 0o44, 'Е': 0o45,
    'Ж': 0o46, 'З': 0o47, 'И': 0o50, 'Й': 0o51, 'К': 0o52, 'Л': 0o53,
    'М': 0o54, 'Н': 0o55, 'О': 0o56, 'П': 0o57, 'Р': 0o60, 'С': 0o61,
    'Т': 0o62, 'У': 0o63, 'Ф': 0o64, 'Х': 0o65, 'Ц': 0o66, 'Ч': 0o67,
    'Ш': 0o70, 'Щ': 0o71, 'Ы': 0o73, 'Ь': 0o74, 'Э': 0o75, 'Ю': 0o76,
    'Я': 0o77,
    ' ': 0o17, '.': 0o16, ',': 0o15, '-': 0o13, '+': 0o12, '/': 0o14,
    '(': 0o22, ')': 0o23, '=': 0o25, '*': 0o31, ':': 0o36, "'": 0o33,
    '0': 0o0, '1': 0o1, '2': 0o2, '3': 0o3, '4': 0o4,
    '5': 0o5, '6': 0o6, '7': 0o7, '8': 0o10, '9': 0o11,
    # латиница (второй регистр ГОСТ, коды 100-117)
    'A': 0o40, 'B': 0o42, 'C': 0o61, 'D': 0o44, 'E': 0o45, 'F': 0o100,
    'G': 0o101, 'H': 0o110, 'I': 0o102, 'J': 0o103, 'K': 0o52, 'L': 0o104,
    'M': 0o54, 'N': 0o105, 'O': 0o56, 'P': 0o57, 'Q': 0o106, 'R': 0o107,
    'S': 0o110, 'T': 0o62, 'U': 0o111, 'V': 0o112, 'W': 0o113, 'X': 0o114,
    'Y': 0o63, 'Z': 0o115,
}


def word_from(text):
    w = 0
    for ch in text:
        w = (w << 6) | GOST_CYR[ch]
    return w


def decode_word(v):
    out = []
    for _ in range(8):
        out.append((v >> 42) & 0o77)
        v = (v << 6) & ((1 << 48) - 1)
    return out


def main():
    path, text = sys.argv[1], sys.argv[2]
    uic = sys.argv[3] if len(sys.argv) > 3 else None
    target = word_from(text)
    tbytes = target.to_bytes(6, 'big')
    with open(path, 'rb') as f:
        data = f.read()
    hits = []
    for a in range(65536):
        off = a * 6
        w = data[off:off + 6]
        if w == tbytes:
            hits.append(a)
    print(f'поиск {text!r} (слово {target:012o}): {len(hits)} попаданий')
    for a in hits:
        # соседние слова для контекста
        ctx = []
        for d in (-2, -1, 1, 2):
            off = (a + d) * 6
            v = int.from_bytes(data[off:off + 6], 'big')
            chars = ''.join(
                next((c for c, g in GOST_CYR.items() if g == x and c.isupper()
                      or c == ' ' and x == 0o17 or not c.isupper() and g == x),
                     '?')
                for x in decode_word(v))
            ctx.append(f'{a+d:05o}:{chars!r}')
        print(f'  {a:05o}  (dec {a})  {"  ".join(ctx)}')
    if uic and hits:
        # кто ссылается на найденные адреса: ищем в uicore инструкции
        # с исполнительным адресом = цель (страница формируется базой),
        # поэтому ищем точное совпадение 12-битного адреса + любой reg
        with open(uic, 'rb') as f:
            ud = f.read()
        for a in hits:
            page, off = divmod(a, 0o1000)
            refs = []
            for q in range(65536):
                c0 = (ud[q * 6] << 16) | (ud[q * 6 + 1] << 8) | ud[q * 6 + 2]
                c1 = (ud[q * 6 + 3] << 16) | (ud[q * 6 + 4] << 8) | ud[q * 6 + 5]
                for c in (c0, c1):
                    if c & 0o7777 == off and c != 0:
                        refs.append(q)
            print(f'  ссылки на смещение {off:04o} (стр. {page:02o}): '
                  f'{len(refs)} ячеек uicore: '
                  + ' '.join(f'{r:05o}' for r in refs[:20]))


if __name__ == '__main__':
    main()
