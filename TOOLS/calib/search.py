#!/usr/bin/env python3
"""Случайный поиск коэффициентов GLAUTO для всех пяти типов."""
import json
import random
import sys
from pathlib import Path

import run_calib as rc
HERE = Path(__file__).resolve().parent

W = HERE / 'searchwork'
W.mkdir(parents=True, exist_ok=True)
if not (W / '2348').exists():
    import shutil
    shutil.copy('/usr/local/share/besm6/2348', W / '2348')
    for f in ('2048', '2053', '2063', '2086', '2099', '2113', '2148',
              '2153', '2222', '2248', '4001'):
        src = Path('/usr/local/share/besm6') / f
        if src.exists():
            (W / f).symlink_to(src)

BASE = [
    [0.50, 0.08,   0, 30, -0.5, 0.040, 0.5],
    [0.50, 0.08, -18, 40, -0.4, 0.060, 0.5],
    [0.50, 0.08,   0, 12, -0.7, 0.025, 0.5],
    [0.20, 0.20, -20, 30, -0.5, 0.040, 0.5],
    [0.20, 0.08, -30,  4, -0.5, 0.040, 0.5],
]

def score(row):
    tip, vert, tch, h, n, oce = row
    tip = tip % 10
    # штраф за жёсткую посадку и за касание до порога
    return abs(vert) + max(0.0, -tch) * 0.02 + (0 if oce <= 3 else 20)

def main():
    random.seed(20261118)
    best = [None] * 5
    best_score = [1e9] * 5
    params = [r[:] for r in BASE]
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    for it in range(n):
        cand = [r[:] for r in params]
        # возмущаем усиления KV, KD, GEw, высоту выравнивания и целевую скорость
        for t in range(5):
            if random.random() < 0.6:
                cand[t][5] = round(params[t][5] * random.uniform(0.3, 2.5), 5)
            if random.random() < 0.6:
                cand[t][6] = round(params[t][6] * random.uniform(0.5, 4.0), 3)
            if random.random() < 0.5:
                cand[t][1] = round(params[t][1] * random.uniform(0.1, 2.0), 5)
            if random.random() < 0.4:
                cand[t][3] = int(max(2, params[t][3] * random.uniform(0.5, 2.0)))
            if random.random() < 0.4:
                cand[t][4] = round(params[t][4] * random.uniform(0.5, 1.5), 4)
        rc.build(W, cand)
        rows = rc.run(W)
        if not rows:
            print('прогон не дал строк', it, flush=True)
            continue
        for row in rows:
            t = row[0] % 10 - 1
            sc = score(row)
            if sc < best_score[t]:
                best_score[t] = sc
                best[t] = (cand[t][:], row)
                params[t] = cand[t][:]
        print('ит=%d scores=%s' % (it, [round(s, 2) for s in best_score]), flush=True)
        (HERE / 'best.json').write_text(
            json.dumps({'best': best, 'params': params, 'scores': best_score}, indent=1))

if __name__ == '__main__':
    main()
