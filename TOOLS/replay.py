#!/usr/bin/env python3
"""Регистратор и повтор прогона тренажёра «Глиссада-6» (этап 7).

Игра ведёт запись кадров X(13), U(4), T и событий в Fortran-регистраторе
`GLRECF.FTN` (COMMON /RECF/, /RECE/, /RECPAR/). Команда инструктора `REC`
включает запись, `RPL` печатает телеметрию, `RST` очищает буфер.

Скрипт прогоняет игру из PERSO зоны 2700, извлекает поток телеметрии
и проверяет, что повторный прогон с теми же параметрами даёт **побайтово
совпадающий** поток. Это и есть контрольная точка этапа 7.

Команды (в скобках — русский псевдоним):
  record/запись NAME [--fault N]   — записать эталон в TOOLS/replays/;
  replay/повтор NAME               — повторить и сравнить с эталоном;
  verify/проверка [NAME] [--fault N] — два прогона и побайтовая сверка;
  list/список                      — список эталонов;
  show/показать NAME               — сводка по эталону.

Пример:
  python3 TOOLS/replay.py проверка
  python3 TOOLS/replay.py запись ту104-штиль --fault 1
  python3 TOOLS/replay.py повтор ту104-штиль
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pty
import re
import select
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DECK = REPO / 'JOB' / 'GLCALL-2700.B6'
LIB = HERE / 'replays'
LIB.mkdir(parents=True, exist_ok=True)
WORK = Path('/tmp/.private/azizz/opencode/replay-run')
WORK.mkdir(parents=True, exist_ok=True)
(WORK / 'GLCALL-2700.B6').write_text(DECK.read_text(encoding='utf-8'),
                                    encoding='utf-8')

# Параметры по умолчанию совпадают с контрольным прогоном install-2348.sh.
DEFAULT = {
    'ktip': 3, 'mode': 1, 'ictrl': 0, 'nfr': 5, 'iflib': 0,
    'tmax': 2400, 'rseed': 7351, 'sigw': 0, 'dt0': 0.60,
}


def answers_for(p: dict, fault: int = 0) -> list[str]:
    """Последовательность ответов PASRED для записи траектории."""
    a = [str(p['ktip']), str(p['mode']), str(p['ictrl']), str(p['nfr']),
         str(p['iflib']), str(p['tmax']), str(p['rseed']), str(p['sigw']),
         str(p['dt0']), 'INS', 'REC']
    if fault:
        a += ['INJ', str(fault)]
    return a + ['STA', 'RPL', 'EXIT']


def run_game(p: dict, fault: int = 0, timeout: int = 240) -> dict:
    answers = answers_for(p, fault)
    master, slave = pty.openpty()
    env = dict(os.environ)
    env['BESM6_PATH'] = str(Path.home() / '.besm6') + ':/usr/local/share/besm6'
    env['PATH'] = '/home/azizz/Yandex.Disk/rezerv/build/dispak:' + env.get('PATH', '')
    proc = subprocess.Popen(['dispak', '-p', 'GLCALL-2700.B6'], cwd=WORK,
                            stdin=slave, stdout=slave, stderr=slave,
                            env=env, close_fds=True)
    os.close(slave)
    buf = b''
    sent = 0
    what = 0
    deadline = time.time() + timeout
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
    (WORK / 'last.log').write_bytes(buf)
    return {'text': buf.decode('utf-8', 'ignore'), 'answers': sent,
            'total': len(answers), 'complete': 'ЗАДАЧИ' in buf.decode('utf-8', 'ignore')}


def extract_telemetry(text: str) -> list[str]:
    """Вырезать поток телеметрии от FRAMES= до последней строки EV/TELE."""
    lines = [l[2:] if l.startswith('> ') else l for l in text.splitlines()]
    start = next((i for i, l in enumerate(lines) if l.startswith('FRAMES=')), None)
    if start is None:
        return []
    end = start
    for i in range(start, len(lines)):
        l = lines[i]
        if (l.startswith('TELE') or l.startswith('EV ') or
                l.startswith('  X=') or l.startswith('  U=') or
                re.match(r'^\s{4,}[-\d]', l)):
            end = i
        elif l.strip() and not lines[i].startswith('>') and i > start + 1:
            # командная подсказка или другой вывод — конец телеметрии
            break
    return [l for l in lines[start:end + 1]
            if (l.startswith('FRAMES=') or l.startswith('TELE') or
                l.startswith('EV ') or l.startswith('  X=') or
                l.startswith('  U=') or re.match(r'^\s{4,}[-\d]', l))]


def digest(tele: list[str]) -> str:
    return hashlib.md5('\n'.join(tele).encode('utf-8')).hexdigest()


def summary(tele: list[str]) -> dict:
    frames = [l for l in tele if l.startswith('TELE')]
    events = [l for l in tele if l.startswith('EV ')]
    head = next((l for l in tele if l.startswith('FRAMES=')), '')
    return {'frames': len(frames), 'events': len(events), 'head': head}


def spec_path(name: str) -> Path:
    return LIB / (name + '.json')


def load(name: str) -> dict:
    p = spec_path(name)
    if not p.exists():
        raise SystemExit('нет эталона: ' + name)
    return json.loads(p.read_text(encoding='utf-8'))


def make_spec(name: str, p: dict, fault: int, tele: list[str], run: dict) -> dict:
    return {
        'name': name, 'params': p, 'fault': fault,
        'created': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'answers': '%d/%d' % (run['answers'], run['total']),
        'complete': run['complete'], **summary(tele),
        'md5': digest(tele), 'telemetry': tele,
    }


def cmd_record(args):
    p = dict(DEFAULT)
    p.update({'sigw': args.sigw, 'rseed': args.rseed})
    if args.ktip:
        p['ktip'] = args.ktip
    run = run_game(p, args.fault)
    tele = extract_telemetry(run['text'])
    if not tele:
        raise SystemExit('телеметрия не получена — проверь REC/RPL в игре')
    spec = make_spec(args.name, p, args.fault, tele, run)
    spec_path(args.name).write_text(json.dumps(spec, ensure_ascii=False, indent=1) + '\n',
                                    encoding='utf-8')
    print('ЗАПИСАНО %s: %s, md5=%s, ответов=%s' %
          (args.name, spec['head'], spec['md5'], spec['answers']))


def cmd_replay(args):
    spec = load(args.name)
    run = run_game(spec['params'], spec.get('fault', 0))
    tele = extract_telemetry(run['text'])
    d1, d2 = spec['md5'], digest(tele)
    if d1 == d2:
        print('СОВПАДЕНИЕ %s: md5=%s, %s' % (args.name, d1, summary(tele)['head']))
        return 0
    print('РАСХОЖДЕНИЕ %s: эталон=%s повтор=%s' % (args.name, d1, d2))
    a, b = spec['telemetry'], tele
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else '<нет строки>'
        y = b[i] if i < len(b) else '<нет строки>'
        if x != y:
            print('  первая разница, строка %d:\n    эталон: %s\n    повтор: %s' %
                  (i + 1, x[:110], y[:110]))
            break
    return 1


def cmd_verify(args):
    p = dict(DEFAULT)
    if args.name:
        spec = load(args.name)
        p = spec['params']
        fault = spec.get('fault', 0)
    else:
        fault = args.fault
    runs = [extract_telemetry(run_game(p, fault)['text']) for _ in range(2)]
    d1, d2 = digest(runs[0]), digest(runs[1])
    ok = len(runs[0]) > 0 and d1 == d2
    print('ПРОВЕРКА %s: md1=%s md2=%s, %s, %s' %
          (args.name or 'основной', d1, d2,
           summary(runs[0])['head'], 'СОВПАДЕНИЕ' if ok else 'РАСХОЖДЕНИЕ'))
    return 0 if ok else 1


def cmd_list(args):
    for f in sorted(LIB.glob('*.json')):
        s = json.loads(f.read_text(encoding='utf-8'))
        print('%-16s %-28s md5=%s кадров=%s событий=%s отказ=%s' %
              (s['name'], s['head'], s['md5'], s['frames'], s['events'],
               s.get('fault', 0)))


def cmd_show(args):
    s = load(args.name)
    print(json.dumps({k: v for k, v in s.items() if k != 'telemetry'},
                     ensure_ascii=False, indent=1))
    print('--- первые 3 строки телеметрии ---')
    print('\n'.join(s['telemetry'][:3]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('record', aliases=['запись'])
    r.add_argument('name')
    r.add_argument('--fault', '--отказ', dest='fault', type=int, default=0)
    r.add_argument('--ktip', type=int, default=0)
    r.add_argument('--sigw', type=float, default=0.0)
    r.add_argument('--rseed', type=int, default=7351)
    p = sub.add_parser('replay', aliases=['повтор']); p.add_argument('name')
    v = sub.add_parser('verify', aliases=['проверка'])
    v.add_argument('name', nargs='?')
    v.add_argument('--fault', '--отказ', dest='fault', type=int, default=0)
    sl = sub.add_parser('list', aliases=['список'])
    sh = sub.add_parser('show', aliases=['показать']); sh.add_argument('name')
    args = ap.parse_args()
    handlers = {
        'record': cmd_record, 'запись': cmd_record,
        'replay': cmd_replay, 'повтор': cmd_replay,
        'verify': cmd_verify, 'проверка': cmd_verify,
        'list': cmd_list, 'список': cmd_list,
        'show': cmd_show, 'показать': cmd_show,
    }
    return handlers[args.cmd](args)


if __name__ == '__main__':
    raise SystemExit(main())
