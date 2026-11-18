#!/usr/bin/env python3
"""Перебор коэффициентов GLAUTO. Принимает JSON-список наборов,
для каждого делает прогон и печатает метрики пяти типов."""
import json
import sys
from pathlib import Path

import run_calib as rc
HERE = Path(__file__).resolve().parent

W = HERE / 'tunework'
W.mkdir(parents=True, exist_ok=True)
if not (W / '2348').exists():
    import shutil
    shutil.copy('/usr/local/share/besm6/2348', W / '2348')
    for f in ('2048', '2053', '2063', '2086', '2099', '2113', '2148',
              '2153', '2222', '2248', '4001'):
        src = Path('/usr/local/share/besm6') / f
        if src.exists():
            (W / f).symlink_to(src)
sets = json.loads(sys.argv[1])
for label, p in sets:
    rows = rc.run(rc.build(W, p) or W)
    print(label, rows, flush=True)
