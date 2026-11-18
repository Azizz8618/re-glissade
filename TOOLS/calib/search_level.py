#!/usr/bin/env python3
"""Поиск коэффициентов GLAUTO для одного уровня турбулентности.

Уровень задаётся переменной CALIB_SIG. Изменяются только три усиления
GE, KV, KD; OFF/HFL/VYF остаются фиксированными для типа.
Результат — levels/sig<уровень>.json.
"""
import json
import os
import random
import sys
from pathlib import Path

import run_calib_level as rc

HERE = Path(__file__).resolve().parent
SIG = float(os.environ.get('CALIB_SIG', '1.5'))
LEVELS = HERE / 'levels'
LEVELS.mkdir(exist_ok=True)
W = HERE / ('search-L' + str(SIG))
W.mkdir(exist_ok=True)
if not (W / '2348').exists():
    import shutil
    shutil.copy('/usr/local/share/besm6/2348', W / '2348')
    for f in ('2048', '2053', '2063', '2086', '2099', '2113', '2148',
              '2153', '2222', '2248', '4001'):
        src = Path('/usr/local/share/besm6') / f
        if src.exists():
            (W / f).symlink_to(src)

BASE = json.loads((HERE / 'best.json').read_text())['params']


def score(row):
    tip, vert, tch, h, n, oce = row
    tip = tip % 10
    s = abs(vert)
    if oce > 2:
        s += 10 * (oce - 2)
    if tch < 0:
        s += 0.02 * abs(tch) + 10
    return s


def main():
    random.seed(20261118 + int(SIG * 100))
    params = [r[:] for r in BASE]
    best = [None] * 5
    best_score = [1e9] * 5
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    for it in range(n):
        cand = [r[:] for r in params]
        for t in range(5):
            cand[t][1] = round(params[t][1] * random.uniform(0.2, 4.0), 6)
            cand[t][5] = round(params[t][5] * random.uniform(0.4, 2.5), 6)
            cand[t][6] = round(params[t][6] * random.uniform(0.4, 3.0), 4)
        rc.build(W, cand)
        rows = rc.run(W)
        if not rows:
            print('ит=%d нет строк' % it, flush=True)
            continue
        for row in rows:
            t = row[0] % 10 - 1
            sc = score(row)
            if sc < best_score[t]:
                best_score[t] = sc
                best[t] = (cand[t][:], row)
                params[t] = cand[t][:]
        print('SIG=%s ит=%d scores=%s' %
              (SIG, it, [round(s, 2) for s in best_score]), flush=True)
        (LEVELS / ('sig%g.json' % SIG)).write_text(json.dumps(
            {'sig': SIG, 'params': params, 'best': best, 'scores': best_score},
            indent=1))


if __name__ == '__main__':
    main()
