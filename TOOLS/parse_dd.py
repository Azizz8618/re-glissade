#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""А2 13.11-6 п.17: парсер drum-дампов dispak (--drum-dump).
Формат: 'в N' - база (начало зоны/тракта N); строки 'к .. ; с u1 u2 u3 u4 ; ADR'
- слово (4 12-бит юнита, восьмеричное), ADR - адрес слова в зоне (восьм.).
'с 0 ; ADR' - нулевое слово. Печать тракта: октал + ISO + ГОСТ-6БИТ."""
import sys, re

GOST = {
 0o40:' ',0o41:'!',0o42:'"',0o43:'№',0o44:'×',0o45:'%',0o46:')',0o47:'€',
 0o50:'@',0o51:'(',0o52:')',0o53:'*',0o54:'+',0o55:',',0o56:'-',0o57:'.',
 0o60:'0',0o61:'1',0o62:'2',0o63:'3',0o64:'4',0o65:'5',0o66:'6',0o67:'7',
 0o70:'8',0o71:'9',0o72:':',0o73:';',0o74:'<',0o75:'=',0o76:'>',0o77:'?',
 0o100:'А',0o101:'Б',0o102:'В',0o103:'Г',0o104:'Д',0o105:'Е',0o106:'Ж',0o107:'З',
 0o110:'И',0o111:'Й',0o112:'К',0o113:'Л',0o114:'М',0o115:'Н',0o116:'О',0o117:'П',
 0o120:'Р',0o121:'С',0o122:'Т',0o123:'У',0o124:'Ф',0o125:'Х',0o126:'Ц',0o127:'Ч',
 0o130:'Ш',0o131:'Щ',0o132:'Ъ',0o133:'Ы',0o134:'Ь',0o135:'Э',0o136:'Ю',0o137:'Я',
 0o140:'а',0o141:'б',0o142:'в',0o143:'г',0o144:'д',0o145:'е',0o146:'ж',0o147:'з',
 0o150:'и',0o151:'й',0o152:'к',0o153:'л',0o154:'м',0o155:'н',0o156:'о',0o157:'п',
 0o160:'р',0o161:'с',0o162:'т',0o163:'у',0o164:'ф',0o165:'х',0o166:'ц',0o167:'ч',
 0o170:'ш',0o171:'щ',0o172:'ъ',0o173:'ы',0o174:'ь',0o175:'э',0o176:'ю',0o177:'я',
}

def iso_str(v):
    out = ''
    for s in (40, 32, 24, 16, 8, 0):
        x = (v >> s) & 0xFF
        if x == 0o12: out += '~'
        elif 32 <= x < 127: out += chr(x)
        elif x == 0: out += '.'
        else: out += f'<{x:03o}>'
    return out

def gost_str(v):
    out = ''
    for s in (36, 30, 24, 18, 12, 6, 0):
        x = (v >> s) & 0x7F
        if x < 0o40:
            out += '.'
        else:
            out += GOST.get(x & 0o177, '?') if x >= 0o40 else '.'
    return out

def parse(path):
    """-> {зона: [(adr_в_зоне, word), ...]}; адрес в файле - сквозной
    восьмеричный, зона = аддрес // 0o2000 (1024 слова = 0o2000)."""
    zones = {}
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.match(r'^[кс]\s+.*;\s*([0-7]+)\s*$', line.strip())
            if not m:
                continue
            a = int(m.group(1), 8)
            zone, adr = a // 0o2000, a % 0o2000
            m2 = re.search(r'с\s+([0-7]+)\s+([0-7]+)\s+([0-7]+)\s+([0-7]+)\s*;', line)
            if m2:
                w = 0
                for g in m2.groups():
                    w = (w << 12) | int(g, 8)
            else:
                w = 0
            zones.setdefault(zone, []).append((adr, w))
    return zones

def show(zones, tract, limit=200):
    z = zones.get(tract)
    if z is None:
        print(f'  (тракт {tract:o} отсутствует/пуст)')
        return
    print(f'  слов: {len(z)}')
    for adr, w in z[:limit]:
        print(f'  {adr:05o}: {w:016o}  {iso_str(w)}  |{gost_str(w)}|')

if __name__ == '__main__':
    path, tract = sys.argv[1], int(sys.argv[2], 8)
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    zones = parse(path)
    print(f'{path}: зон={len(zones)}, тракт {tract:o}:')
    show(zones, tract, limit)
