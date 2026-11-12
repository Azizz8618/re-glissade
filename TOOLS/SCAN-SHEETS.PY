#!/usr/bin/env python3
# Шаг 1: скан томов dispak (zone_t) на аутентичные листы входного потока.
# Признаки: заголовки 0o2204240/0o2104140, ISO-ключи REC/BSP/EOF/SEF/ADD/END/RWN,
# маркеры [11200]=0o3000000000000000 / [11201]=0o6000000000000000.
import struct, sys, glob, os

M48 = (1<<48)-1
def words_of_zone(chunk):
    return struct.unpack('<1024Q', chunk[64:])

def word48(w): return w & M48

KEYS = [b'REC', b'BSP', b'EOF', b'SEF', b'ADD', b'END', b'RWN']
def key_at(w, off):
    # ISO 8 бит, старший байт первым: байты по 6 на слово
    b = [(w >> (40-8*i)) & 0xFF for i in range(6)]
    s = bytes(b)
    for k in KEYS:
        if s.startswith(k):
            return s
    return None

HEADERS = {0o2204240: 'HDR-A', 0o2104140: 'HDR-B',
           0o3000000000000000: 'MKR[11200]', 0o6000000000000000: 'MKR[11201]'}

def scan(path):
    data = open(path,'rb').read()
    if len(data) % 8256 or len(data) < 8256:
        return
    nz = len(data)//8256
    hits = {}
    for z in range(nz):
        chunk = data[z*8256:(z+1)*8256]
        # пропустить полностью нулевые контрольные слова? cwords могут быть нулевыми и у данных
        ws = words_of_zone(chunk)
        for i, w in enumerate(ws):
            v = word48(w)
            tag = HEADERS.get(v)
            if tag:
                hits.setdefault(tag, []).append((z,i))
            s = key_at(v, 0)
            if s:
                hits.setdefault('KEY '+s[:3].decode(), []).append((z,i,s))
    if hits:
        print(f'== {path} (зон {nz})')
        for tag, lst in hits.items():
            print(f'   {tag}: {len(lst)} слов; первые: ' +
                  ', '.join(f'з{z:04o} сл{i:04o}' + (f' {s!r}' if isinstance(t,tuple) and len(t)>2 else '')
                            for (z,i,*t) in [(x[0],x[1],*x[2:]) for x in lst[:6]]))

for p in sorted(glob.glob(sys.argv[1])):
    try: scan(p)
    except Exception as e: print(p, 'ошибка:', e)
