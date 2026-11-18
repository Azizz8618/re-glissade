#!/usr/bin/env python3
"""Прогон задачи ПВС на эмулируемой СМ-2.

Использование:
  python3 TOOLS/ps2_run.py <script.ini> [--sim=<путь к hp2100>] [--timeout=60]

Скрипт подаётся в `hp2100 -p`, вывод сохраняется в <script>.out.
На stdout печатаются строки `EXAMINE`, признаки останова и код выхода.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_SIM = '/home/azizz/Yandex.Disk/simh/BIN/hp2100'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('script', help='SIMH .ini-скрипт с SET CPU SM2 и DEPOSIT-ами')
    ap.add_argument('--sim', default=DEFAULT_SIM, help='путь к бинарнику hp2100')
    ap.add_argument('--timeout', type=int, default=60, help='таймаут в секундах')
    args = ap.parse_args()

    script = Path(args.script)
    if not script.exists():
        print('СТОП: нет скрипта ' + str(script), file=sys.stderr)
        return 2
    if not Path(args.sim).exists():
        print('СТОП: нет симулятора ' + args.sim, file=sys.stderr)
        return 2

    work = script.parent
    out = work / (script.stem + '.out')
    env = dict(os.environ)
    env['BESM6_PATH'] = str(Path.home() / '.besm6') + ':/usr/local/share/besm6'
    proc = subprocess.run([args.sim, '-p', script.name], cwd=work, env=env,
                          input=b'', stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=args.timeout)
    text = proc.stdout.decode('utf-8', 'ignore').replace('Е', 'E')
    out.write_text(text, encoding='utf-8')

    for line in text.splitlines():
        if ('EXAMINE' in line or 'HALT' in line or 'Goodbye' in line or
                'СМ2' in line or 'SM2' in line or 'Error' in line):
            print(line.strip()[:160])

    values = re.findall(r'^\s*([0-7]+):\s+([0-7]+)', text, re.MULTILINE)
    for addr, word in values:
        print('EXAMINE %s = %s' % (addr, word))
    print('Найдено значений EXAMINE:', len(values))
    return proc.returncode


if __name__ == '__main__':
    raise SystemExit(main())
