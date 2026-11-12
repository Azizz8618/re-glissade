#!/usr/bin/env python3
# Шаг 3 (план А2): том 202 = [заголовок члена-листа 4023/з0o554 verbatim
# (сл.0..0o14, conv=1)] + [тело = ТОЧНАЯ КОПИЯ СПУЛА МОНЫ из core-дампа
# (слова 0o76000..0o76161: колода с картами данных, ISO-8бит, EOR,
# конец 0o7760000000000012), conv=2].
# Спул снимается: BESM6_CORE_ON_PC=37402 (прогон NL45-колоды).
# Использование: mk_tom45g.py <core-pc.bin> <файл тома> [число зон]
import sys

ZONE_OFFSET = 4
CONV_CMD = 1
CONV_DATA = 2

# аутентичный заголовок (том 4023/з0o554, сл.0..0o14, conv=1)
HEADER = [0o0000000000022015,
          0o6400000000000000, 0o6000000000000000, 0o5400000000000000,
          0o5000000000000000, 0o4400000000000000, 0o4000000000000000,
          0o1400000000000000, 0o2000000000000000, 0o2400000000000000,
          0o3000000000000000, 0o3400000000000000, 0o4000000000000000,
          0o4000000000000000]


def main():
    core, tom = sys.argv[1], sys.argv[2]
    nzones = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    data = open(core, 'rb').read()
    w = [int.from_bytes(data[i*6:(i+1)*6], 'big') for i in range(32768)]
    # спул: слова буфера обмена 76000.. до конца полезных данных
    body = []
    for a in range(0o76000, 0o77777):
        v = w[a]
        body.append(v)
        if v == 0o7760000000000012:      # слово конца потока МОНЫ
            break
    print(f'спул: {len(body)} слов (0o76000..0o{0o76000+len(body)-1:05o})')
    nz = len(data)//6
    print(f'  [76000] = {body[0]:016o}')
    print(f'  [последнее] = {body[-1]:016o}')

    zone = [0]*1024
    conv = [CONV_DATA]*1024
    for i, h in enumerate(HEADER):
        zone[i] = h
        conv[i] = CONV_CMD
    zone[HDR_MARK_POS] = MARK_END if variant == 'f1' else MARK_CONT
    pos = len(HEADER)                  # 0o15
    for v in body:
        if pos >= 1024:
            break
        zone[pos] = v
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


if __name__ == '__main__':
    main()
