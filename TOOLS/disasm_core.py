#!/usr/bin/env python3
# Ручное дизассемблирование дампа памяти задачи (core-a4.bin) без
# потокового анализа: каждая 48-бит ячейка = две 24-бит команды.
# Раскладка - по макросам dispak (defs.h): М(4) струк(1) расш(1) К(6) А(12).
# Использование: disasm_core.py <файл.bin> <начало-восьм.> <конец-восьм.>

import sys

# обычные команды (код 6 бит), имена = dispak/optab.c
EXTNAMES = {
    0o00: 'atx', 0o01: 'stx', 0o02: 'mod', 0o03: 'xts',
    0o04: 'a+x', 0o05: 'a-x', 0o06: 'x-a', 0o07: 'amx',
    0o10: 'xta', 0o11: 'aax', 0o12: 'aex', 0o13: 'arx', 0o14: 'avx',
    0o15: 'aox', 0o16: 'a/x', 0o17: 'a*x', 0o20: 'apx', 0o21: 'aux',
    0o22: 'acx', 0o23: 'anx', 0o24: 'e+x', 0o25: 'e-x', 0o26: 'asx',
    0o27: 'xtr', 0o30: 'rte', 0o31: 'yta', 0o32: 'ext', 0o33: 'ext',
    0o34: 'e+n', 0o35: 'e-n', 0o36: 'asn', 0o37: 'ntr', 0o40: 'ati',
    0o41: 'sti', 0o42: 'ita', 0o43: 'its', 0o44: 'mtj', 0o45: 'm+j',
    0o46: 'x46', 0o47: '*47',
}
for n in range(0o50, 0o100):
    EXTNAMES[n] = 'Э%02o' % n

# структурные команды (струк-бит=1, код 5 бит | 0o100)
EXTNAMES2 = {
    0o100: '*20', 0o101: '*21', 0o102: 'utc', 0o103: 'wtc',
    0o104: 'vtm', 0o105: 'utm', 0o106: 'uza', 0o107: 'u1a',
    0o110: 'uj', 0o111: 'vjm', 0o112: 'iret', 0o113: 'stop',
    0o114: 'vzm', 0o115: 'v1m', 0o116: 'X36', 0o117: 'vlm',
}


def decode_half(b):
    b0, b1, b2 = b
    reg = b0 >> 4
    struct = b0 & 8
    exp = b0 & 4
    op2 = (((b1 >> 4) | (b0 << 4)) & 0o77)
    op1 = (((b1 >> 7) | (b0 << 1)) & 0o17)
    opcode = (op1 | 0o100) if struct else op2
    if struct:
        addr = ((b1 << 8) | b2) & 0o77777      # структурные: 15 бит
    else:
        addr = ((b1 << 8) | b2) & 0o7777
        if exp:
            addr |= 0o70000
    return opcode, reg, addr


def fmt(op, reg, addr):
    if op >= 0o100:
        name = EXTNAMES2.get(op, 'Э%o' % (op - 0o100))
    else:
        name = EXTNAMES.get(op, '??%02o' % op)
    return '%-5s %04o(%o)' % (name, addr, reg)


def main():
    path, a0, a1 = sys.argv[1], int(sys.argv[2], 8), int(sys.argv[3], 8)
    with open(path, 'rb') as f:
        data = f.read()
    for a in range(a0, a1 + 1):
        off = a * 6
        b = data[off:off + 6]
        if len(b) < 6:
            break
        opl, rl, al = decode_half(b[0:3])
        opr, rr, ar = decode_half(b[3:6])
        print('%05o  %-12s | %-12s ; %016o' % (
            a, fmt(opl, rl, al), fmt(opr, rr, ar), int.from_bytes(b, 'big')))


if __name__ == '__main__':
    main()
