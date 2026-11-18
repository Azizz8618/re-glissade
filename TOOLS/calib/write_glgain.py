#!/usr/bin/env python3
"""Собрать SRC/GLGAIN.FTN из best.json и levels/sig*.json.

В блоке /APGAIN/ хранятся по пять уровней турбулентности:
  SLVL — значения SIGW;
  PGE, PKV, PKD — усиления для каждого типа;
  CG — признак подавления вертикального порыва (0/1).
"""
import json
import sys
from pathlib import Path


def emit_data(out, elems, vals):
    """DATA-оператор с продолжениями строк <=72."""
    tokens = [e + ',' for e in elems[:-1]] + [elems[-1] + ' /'] + \
             [v + ',' for v in vals[:-1]] + [vals[-1] + ' /']
    line = '      DATA'
    for tok in tokens:
        add = ' ' + tok
        if len(line) + len(add) > 71:
            out += line + '\n'
            line = '     1' + tok
        else:
            line += add
    return out + line + '\n'


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
LEVELS = [0.0, 0.3, 0.5, 1.0, 1.5]


def gval(path):
    return json.loads(Path(path).read_text())


def fmt(v):
    return ('%g' % v)


def main():
    out = '''C==============================================================
C     ГЛИССАДА-6. БЛОК УСИЛЕНИЙ АВТОПИЛОТА ПО ПОГОДЕ.
C     ГЕНЕРИРУЕТСЯ: TOOLS/CALIB/WRITE_GLGAIN.PY.
C     НЕ ПРАВИТЬ ВРУЧНУЮ — ПРАВИТЬ TOOLS/CALIB/LEVELS/*.JSON.
C==============================================================
      BLOCK DATA GLGAIN
      COMMON /APGAIN/ PGE(5,5),PKV(5,5),PKD(5,5),CG(5,5),SLVL(5)
'''
    # строка 1 (штиль) — из best.json
    calm = [r[:] for r in gval(HERE / 'best.json')['params']]
    # при SIGW=0 в GLAUTO использовался GE, а не GEW:
    for r, ge in zip(calm, [0.5, 0.5, 0.5, 0.2, 0.2]):
        r[1] = ge
    rows = [calm]
    for sig in LEVELS[1:]:
        f = HERE / 'levels' / ('sig%g.json' % sig)
        rows.append(gval(f)['params'])
    for name, idx in (('PGE', 1), ('PKV', 5), ('PKD', 6)):
        for level, row in enumerate(rows, 1):
            vals = [fmt(r[idx]) for r in row]
            elems = ','.join('%s(%d,%d)' % (name, level, i) for i in range(1, 6))
            out = emit_data(out, ['%s(%d,%d)' % (name, level, i) for i in range(1, 6)], vals)
    # CG = 0 (пока подавление порыва не включено ни на одном уровне)
    for level in range(1, 6):
        elems = ['CG(%d,%d)' % (level, i) for i in range(1, 6)]
        out = emit_data(out, elems, ['0'] * 5)
    out += '      DATA SLVL /%s/\n' % ', '.join(fmt(x) for x in LEVELS)
    out += '      END\n'
    target = REPO / 'SRC' / 'GLGAIN.FTN'
    target.write_text(out, encoding='utf-8')
    bad = [(i, len(l)) for i, l in enumerate(out.split('\n'), 1) if len(l) > 72]
    if bad:
        raise SystemExit('строки >72: %s' % bad[:5])
    print('записано', target, out.count('\n'), 'строк')


if __name__ == '__main__':
    main()
