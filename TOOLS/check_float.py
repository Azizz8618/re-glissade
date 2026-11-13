#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# п.18.15(1): проверка значений B(1..4), записанных на 03201 в [1121..1124],
# по формуле get_real() из dispak/arith.c:
#   exponent = (word.l >> 17) - 64          # word.l = старшие 24 бита
#   mantissa = ((int64)word.l << 24 | word.r) << (64-48+7)
#   value    = ldexp(mantissa, exponent-63) # = word48 * 2^(e-40)
# Слово хранится как 48-бит int; word.l>>17 = старшие 7 бит = порядок+64.
def get_real(word48):
    word48 &= (1 << 48) - 1
    e = (word48 >> 41) - 64                 # старшие 7 бит (биты 1-7)
    # знаковое расширение 48-битного слова (мантисса доп. код)
    if word48 & (1 << 47):
        word48 -= 1 << 48
    mantissa = word48 << (64 - 48 + 7)      # в int64
    return ldexp(mantissa, e - 63)

import math
ldexp = math.ldexp

words = [
    (0o4611300000000000, 'B1? ожидали 2400.0'),
    (0o4656267000000000, 'B2? ожидали 7351.0'),
    (0o4054000000000000, 'B3? ожидали 1.5'),
    (0o4011463146314632, 'B4? ожидали 0.60'),
]
for w, note in words:
    v = get_real(w)
    print("0o%016o  e=%d  value = %.10g   (%s)" % (w, (w >> 41) - 64, v, note))

print()
# обратная задача: как выглядят эталонные числа в этом формате
def mk_real(x, e):
    # value = mant48 * 2^(e-40), mant48 = x / 2^(e-40)
    m = x / (2.0 ** (e - 40))
    wi = int(round(m))
    if wi < 0:
        wi += 1 << 48
    return wi

for x, e, nm in ((2400.0, 12, '2400 p=12'), (2400.0, 0, '2400 p=0'),
                 (7351.0, 13, '7351 p=13'), (1.5, 1, '1.5 p=1'),
                 (0.6, 0, '0.6 p=0'), (1.0, 0, '1.0 p=0')):
    print("%-12s -> 0o%016o" % (nm, mk_real(x, e) & ((1<<48)-1)))
