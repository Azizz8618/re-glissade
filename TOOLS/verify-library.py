#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка библиотеки на томе 2348 и чистого прогона игры.

Использование:
    python3 TOOLS/verify-library.py <каталог-с-образами> [диспак]

Проверяет:
  1. зона 3000(8) тома 2348 содержит каталог с ATM и NR;
  2. образ 2348 изменён только в зонах 3000–3047(8);
  3. игра с GLNUM (вызовы СБ) завершается чисто, без ОТСУТСТВУЕТ
     и ошибок 201/205.
"""
import os
import subprocess
import sys
from pathlib import Path

ZONE = 8256
LIB_START = 0o3000
LIB_END = 0o3047
REPO = Path(__file__).resolve().parent.parent
SIPROD_TOOLS = Path('/home/azizz/Yandex.Disk/re-siprod/tools')


def read_catalog(path):
    sys.path.insert(0, str(SIPROD_TOOLS))
    from siprod_lib import Library
    return Library(str(path)).catalog


def main():
    if len(sys.argv) < 2:
        sys.exit('нужен каталог с образами дисков')
    work = Path(sys.argv[1]).resolve()
    dispak = sys.argv[2] if len(sys.argv) > 2 else '/tmp/.private/azizz/opencode/dispak-86c7/build/dispak/dispak'
    backup = Path('/tmp/.private/azizz/opencode/2348-original.bak')

    ok = True
    # 1. каталог
    check = Path('/tmp/verify-z3000.bin')
    cmd = [str(Path(dispak).parent.parent / 'besmtool' / 'besmtool'),
           'dump', '2348', '--start=1536', '--length=3', '--to-file=' + str(check)]
    env = dict(os.environ); env['BESM6_PATH'] = str(work)
    r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True)
    if r.returncode:
        print('ОШИБКА: не удалось прочитать зону 3000:', r.stderr.strip())
        ok = False
    else:
        cat = read_catalog(check)
        for name in ('ATM', 'NR'):
            present = name in cat
            print(f'зона 3000: {name} — ' + ('есть' if present else 'НЕТ'))
            ok &= present
        print(f'записей в каталоге: {len(cat)}')

    # 2. диапазон изменённых зон
    if backup.exists():
        a = backup.read_bytes()
        b = (work / '2348').read_bytes()
        if len(a) == len(b):
            diffs = [i for i in range(len(a)) if a[i] != b[i]]
            if diffs:
                lo, hi = min(diffs) // ZONE - 4, max(diffs) // ZONE - 4
                good = lo == LIB_START and hi == LIB_END
                print(f'изменённые зоны: {lo:o}..{hi:o} — ' + ('OK' if good else 'НЕ ОК'))
                ok &= good
            else:
                print(' ОШИБКА: образ 2348 не изменён')
                ok = False

    # 3. прогон игры с GLNUM
    deck = work / 'deck-glnum.B6'
    if deck.exists():
        env.update({
            'BESM6_LUN45_DRUM': '020', 'BESM6_LUN45_TRACT': '04',
            'BESM6_LUN46_DRUM': '020', 'BESM6_LUN46_TRACT': '05',
            'BESM6_LUN_TAIL': '06', 'BESM6_DECK': str(deck),
            'BESM6_EXIT_ADDR': '437',
            'BESM6_DRUM_SEED': str(work / 'seed.bin'),
            'BESM6_DRUM_SEED_DRUM': '020',
            'PATH': '/usr/bin:/bin',
        })
        r = subprocess.run([dispak, '--path=.', str(deck)], cwd=work, env=env,
                           capture_output=True, text=True, errors='replace',
                           timeout=180)
        out = r.stdout
        checks = {
            'ОТСУТСТВУЕТ': out.count('ОТСУТСТВУЕТ'),
            'ошибка 201': out.count('ЕRRОR 201'),
            'ошибка 205': out.count('ЕRRОR 205'),
            'ОЦЕНКА': out.count('ОЦЕНКА'),
            'завершение 411': out.count('00411:'),
        }
        for k, v in checks.items():
            print(f'{k}: {v}')
        ok &= checks['ОТСУТСТВУЕТ'] == 0
        ok &= checks['ошибка 201'] == 0
        ok &= checks['ошибка 205'] == 0
        ok &= checks['ОЦЕНКА'] > 0
        ok &= checks['завершение 411'] > 0

    print('\nИТОГ: ' + ('ПРОЙДЕНО' if ok else 'НЕ ПРОЙДЕНО'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
