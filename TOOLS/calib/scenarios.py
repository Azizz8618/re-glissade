#!/usr/bin/env python3
"""Исторические сценарии посадки с заданными погодными условиями.

Сценарий — JSON-файл в scenarios/. Он задаёт тип самолёта, погоду
(SIGW, RSEED), тягу и ожидаемые метрики эталонной посадки. Скрипт
прогоняет сценарий в самой игре (PERSO, зона 2700) и сверяет результат.

Команды:
  list              — список сценариев;
  add ID ...        — создать сценарий (без ожидаемых метрик);
  run ID            — прогон одного сценария, печать метрик;
  capture ID        — прогон и запись измеренных метрик как ожидаемых;
  verify [ID]       — прогон всех (или одного) со сверкой;
  report            — Markdown-отчёт в docs/analysis/etalon-scenarios.md.

Пример:
  python3 scenarios.py add tu104-rle --aircraft 3 --sigw 0.3 \\
      --rseed 7351.5 --name "Ту-104 по РЛЭ" --source "РЛЭ Ту-104, стр. 58"
  python3 scenarios.py capture tu104-rle
  python3 scenarios.py verify
"""
from __future__ import annotations

import argparse
import json
import os
import pty
import re
import select
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCEN = HERE / 'scenarios'
SCEN.mkdir(exist_ok=True)
REPO = HERE.parent.parent
DECK = REPO / 'JOB' / 'GLCALL-2700.B6'
WORK = Path('/tmp/.private/azizz/opencode/scenarios-run')
WORK.mkdir(parents=True, exist_ok=True)
(WORK / 'GLCALL-2700.B6').write_text(DECK.read_text(encoding='utf-8'), encoding='utf-8')

NAMES = {1: 'МиГ-15', 2: 'Ил-28', 3: 'Ту-104', 4: 'Ан-24', 5: 'Ан-2'}
DISPAK_DIR = '/home/azizz/Yandex.Disk/rezerv/build/dispak'


def load(scid):
    f = SCEN / (scid + '.json')
    if not f.exists():
        raise SystemExit('нет сценария: %s' % f)
    return json.loads(f.read_text(encoding='utf-8'))


def save(sc):
    (SCEN / (sc['id'] + '.json')).write_text(
        json.dumps(sc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def run_game(sc, timeout=240):
    """Прогон сценария в диалоговой игре. Возвращает метрики."""
    answers = [
        str(sc['aircraft']), '1', '0', '5', '0',
        str(sc['limits'].get('tmax', 2400)),
        str(sc['weather']['rseed']),
        str(sc['weather']['sigw']),
        str(sc['weather']['dt0']),
        'STA', 'EXIT',
    ]
    master, slave = pty.openpty()
    env = dict(os.environ)
    env['BESM6_PATH'] = str(Path.home() / '.besm6') + ':/usr/local/share/besm6'
    env['PATH'] = DISPAK_DIR + ':' + env.get('PATH', '')
    log = WORK / (sc['id'] + '.log')
    proc = subprocess.Popen(['dispak', '-p', 'GLCALL-2700.B6'], cwd=WORK,
                            stdin=slave, stdout=slave, stderr=slave,
                            env=env, close_fds=True)
    os.close(slave)
    buf = b''
    sent = 0
    what = 0
    deadline = time.time() + timeout
    with log.open('wb') as out:
        while time.time() < deadline:
            ready, _, _ = select.select([master], [], [], 0.5)
            if ready:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                out.write(chunk)
                out.flush()
                text = buf.decode('utf-8', 'ignore')
                n = text.count('WНАТ=')
                if n > what:
                    for _ in range(n - what):
                        os.write(master, b'L0\n' if what == 0 else b'\n')
                    what = n
                np = text.count('\n-\r')
                while sent < len(answers) and np > sent:
                    os.write(master, (answers[sent] + '\n').encode())
                    sent += 1
            if proc.poll() is not None:
                break
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    os.close(master)
    text_raw = buf.decode('utf-8', 'ignore')
    text = text_raw.replace('Е', 'E')

    def last(pattern):
        m = re.findall(pattern, text)
        return float(m[-1]) if m else None

    return {
        'vert': last(r'VERT=\s*([-\d.E+]+)'),
        'ocenka': int(last(r'OCENKA=\s*(\d+)')) if last(r'OCENKA=\s*(\d+)') else None,
        'daln': last(r'DALN=\s*([-\d.E+]+)'),
        't': last(r'(?m)^T=\s*([-\d.E+]+)'),
        'answers': sent,
        'complete': 'ЗАДАЧИ' in text_raw,
    }


def cmd_list(args):
    files = sorted(SCEN.glob('*.json'))
    if not files:
        print('сценариев нет')
        return
    print('%-22s %-8s %-6s %-8s %-10s' % ('ID', 'самолёт', 'SIGW', 'RSEED', 'OCENKA'))
    for f in files:
        sc = json.loads(f.read_text(encoding='utf-8'))
        e = sc.get('expected') or {}
        print('%-22s %-8s %-6s %-8s %-10s' % (
            sc['id'], NAMES.get(sc['aircraft'], sc['aircraft']),
            sc['weather']['sigw'], sc['weather']['rseed'],
            e.get('ocenka', '—')))


def cmd_add(args):
    if (SCEN / (args.id + '.json')).exists():
        raise SystemExit('сценарий уже есть: %s' % args.id)
    sc = {
        'id': args.id,
        'name': args.name or args.id,
        'source': args.source or '',
        'aircraft': args.aircraft,
        'weather': {'sigw': args.sigw, 'rseed': args.rseed, 'dt0': args.dt0},
        'limits': {'tmax': args.tmax},
        'tolerance': {'vert': 0.05, 'daln': 50.0},
        'expected': None,
    }
    save(sc)
    print('создан', SCEN / (sc['id'] + '.json'))


def cmd_run(args):
    sc = load(args.id)
    r = run_game(sc)
    print('%s (%s): VERT=%s OCENKA=%s DALN=%s T=%s ответов=%d завершение=%s'
          % (sc['id'], NAMES.get(sc['aircraft'], '?'), r['vert'], r['ocenka'],
             r['daln'], r['t'], r['answers'], r['complete']))
    return r


def cmd_capture(args):
    sc = load(args.id)
    r = run_game(sc)
    if r['vert'] is None or r['ocenka'] is None:
        raise SystemExit('прогон не дал метрик — нечего записывать')
    sc['expected'] = {k: r[k] for k in ('vert', 'ocenka', 'daln', 't')}
    save(sc)
    print('записано expected:', sc['expected'])


def cmd_verify(args):
    ids = [args.id] if args.id else sorted(f.stem for f in SCEN.glob('*.json'))
    ok = bad = 0
    for scid in ids:
        sc = load(scid)
        exp = sc.get('expected')
        r = run_game(sc)
        if not exp:
            print('%-22s ПРОПУСК (нет expected): OCENKA=%s' % (scid, r['ocenka']))
            continue
        tol = sc.get('tolerance', {})
        dv = abs(r['vert'] - exp['vert']) if r['vert'] is not None and exp.get('vert') is not None else 9e9
        dd = abs(r['daln'] - exp['daln']) if r['daln'] is not None and exp.get('daln') is not None else 9e9
        good = (r['ocenka'] == exp['ocenka'] and
                dv <= tol.get('vert', 0.05) and
                dd <= tol.get('daln', 50.0) and r['complete'])
        print('%-22s %s VERT %s/%s DALN %s/%s OCENKA %s/%s' % (
            scid, 'OK' if good else 'ОТКЛОНЕНИЕ',
            r['vert'], exp['vert'], r['daln'], exp['daln'],
            r['ocenka'], exp['ocenka']))
        ok += good
        bad += not good
    print('итого: OK=%d, отклонений=%d' % (ok, bad))


def cmd_report(args):
    lines = ['# ИСТОРИЧЕСКИЕ СЦЕНАРИИ ПОСАДКИ', '',
             'Сценарии описаны в `TOOLS/calib/scenarios/*.json` и',
             'запускаются в реальной игре: `python3 TOOLS/calib/scenarios.py verify`.', '',
             'DALN — дальность до порога в момент касания; отрицательное',
             'значение означает касание за порогом. VERT — вертикальная скорость, м/с.', '',
             'Сценарии воспроизводят **условия захода** (погоду, тягу), а не',
             'исход происшествия: в модели нет видимости, рельефа, бокового',
             'уклонения и капотирования. Мягкая посадка в сценарии не означает',
             'благополучного исхода в реальности. В сценарии',
             '`mig15-storm-1952` модель даёт оценку 4: успешная посадка на',
             'рисовое поле в реальности не воспроизводится — это предел',
             'текущего закона управления при SIGW=1.5.', '',
             '| ID | Самолёт | Источник | URL | SIGW | VERT | OCENKA |',
             '|---|---|---|---|---|---|---|']
    for f in sorted(SCEN.glob('*.json')):
        sc = json.loads(f.read_text(encoding='utf-8'))
        e = sc.get('expected') or {}
        lines.append('| %s | %s | %s | %s | %s | %s | %s |' % (
            sc['id'], NAMES.get(sc['aircraft'], '?'), sc.get('source', ''),
            sc.get('url', '—'), sc['weather']['sigw'],
            e.get('vert', '—'), e.get('ocenka', '—')))
    out = REPO / 'docs' / 'analysis' / 'etalon-scenarios.md'
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('записано', out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    a = sub.add_parser('add')
    a.add_argument('id')
    a.add_argument('--aircraft', type=int, choices=(1, 2, 3, 4, 5), required=True)
    a.add_argument('--sigw', type=float, required=True)
    a.add_argument('--rseed', type=float, required=True)
    a.add_argument('--dt0', type=float, default=0.60)
    a.add_argument('--tmax', type=float, default=2400)
    a.add_argument('--name', default='')
    a.add_argument('--source', default='')
    for name in ('run', 'capture'):
        sub.add_parser(name).add_argument('id')
    v = sub.add_parser('verify')
    v.add_argument('id', nargs='?')
    sub.add_parser('report')
    args = ap.parse_args()
    {'list': cmd_list, 'add': cmd_add, 'run': cmd_run, 'capture': cmd_capture,
     'verify': cmd_verify, 'report': cmd_report}[args.cmd](args)


if __name__ == '__main__':
    main()
