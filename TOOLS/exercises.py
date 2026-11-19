#!/usr/bin/env python3
"""Библиотека упражнений тренажёра «Глиссада-6».

Упражнение — JSON в TOOLS/exercises/. Оно задаёт тип самолёта, погоду,
Seed, тягу и цель посадки. Скрипт прогоняет упражнение в реальной игре
из PERSO зоны 2700 и сверяет метрики с целью.

Команды:
  list            — список упражнений;
  show N          — параметры упражнения N (T1…T5 или номер);
  run N           — прогон;
  verify [N]      — прогон со сверкой с целью;
  score           — оценка задания по каждому упражнению (GLSCORE);
  report          — Markdown-отчёт.

Пример:
  python3 TOOLS/exercises.py verify T1
  python3 TOOLS/exercises.py verify
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import pty
import re
import select
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LIB = HERE / 'exercises'
DECK = REPO / 'JOB' / 'GLCALL-2700.B6'
WORK = Path('/tmp/.private/azizz/opencode/exercises-run')
WORK.mkdir(parents=True, exist_ok=True)
(WORK / 'GLCALL-2700.B6').write_text(DECK.read_text(encoding='utf-8'), encoding='utf-8')

NAMES = {1: 'МиГ-15', 2: 'Ил-28', 3: 'Ту-104', 4: 'Ан-24', 5: 'Ан-2'}

# --- Параметры ручного пилота (упражнения с полем pilot="manual") ---------
MANUAL = {
    'path_k': 0.05241,      # уклон глиссады
    'ge': 0.15,             # усиление по отклонению от глиссады
    'kv': 0.05,             # усиление по вертикальной скорости
    'de_start': 0.0,        # начальное положение руля высоты
    'dtz_start': 0.6,       # начальная тяга
    'vthr': 72.0,           # скорость захода МиГ-15
    'flare_h': 100.0,       # высота начала выравнивания, м
    'flare_de': 0.08,       # добавка руля при выравнивании
    'de_max': 0.15,         # предел руля высоты
    'de_min': -0.05,        # нижний предел руля высоты
    'dtz_max': 1.0,         # предел тяги
    'cmd_step': 0.05,       # шаг одной команды EV/TH/AI
    'step_group': 10,       # шагов STE между решениями пилота
    'ky': 0.0,              # усиление по Y (элероны отключены: см. отчёт)
    'kvy': 0.0,             # усиление по dY/dt
    'kw': 0.0,              # демпфер по крену
    'vy_alpha': 0.5,        # сглаживание оценки боковой скорости
    'roll_a': 30.0,         # WX'=a*DA-b*WX, МиГ-15: QBAR*S*BB*CLDA/JX
    'roll_b': 3.2,          # аэродинамическое демпфирование крена
    'da_max': 0.15,         # предел отклонения элеронов
    'da_min': -0.15,        # нижний предел отклонения элеронов
}


def load_all():
    out = []
    for f in sorted(LIB.glob('*.json')):
        out.append(json.loads(f.read_text(encoding='utf-8')))
    return out


def find(key):
    for e in load_all():
        if key in (e['id'], str(e['number'])):
            return e
    raise SystemExit('нет упражнения: ' + key)


def parse_frame(text):
    """Достать последние метрики из кадра АЦПУ.

    Разбирается только хвост буфера: за один кадр АЦПУ приходится около
    700 знаков, поэтому четырёх тысяч достаточно для трёх последних кадров.
    """
    text = text[-4000:]
    # Число должно быть полным: хвост буфера может оборвать экспоненту.
    num = r'([+\-]?\d*\.?\d+(?:E[+\-]?\d+)?)\s+'
    rows = re.findall(
        r'T=\s*' + num + r'TIP=\d+\s+DALN=\s*' + num +
        r'VYS=\s*' + num + r'Y=\s*' + num, text)
    speeds = re.findall(r'SKOR=\s*' + num + r'VERT=\s*' + num, text)
    if not rows or not speeds:
        return None
    t, daln, vys, y = (float(x.replace(' ', '')) for x in rows[-1])
    skor, vert = (float(x.replace(' ', '')) for x in speeds[-1])
    return {'t': t, 'daln': daln, 'vys': vys, 'skor': skor,
            'vert': vert, 'y': y}


def _drive(out, state, key, goal, plus, minus, cap=6):
    """Приблизить канал key к цели командами с шагом cmd_step."""
    step = MANUAL['cmd_step']
    for _ in range(cap):
        if abs(state[key] - goal) < step / 2:
            break
        cmd = plus if goal > state[key] else minus
        out.append(cmd)
        state[key] += step if cmd == plus else -step


def manual_decision(frame, state):
    """Закон ручного пилота: DE/DTZ по глиссаде, DA по боковому отклонению.

    Боковой контур повторяет эталон GLAUTO: DA = -ky*Y - kvy*dY/dt - kw*WX.
    Боковая скорость оценивается по разности Y между кадрами, а скорость
    крена WX — интегрированием модели WX'=a*DA-b*WX с известными
    производными МиГ-15 (в кадре АЦПУ угловые скорости не печатаются).
    Знак отрицательный: при уходе вправо (Y>0) элероны отклоняются AI-.
    """
    out = []
    egli = frame['vys'] - frame['daln'] * MANUAL['path_k']
    vyc = -MANUAL['path_k'] * frame['skor'] - MANUAL['ge'] * egli
    de_goal = -MANUAL['kv'] * (frame['vert'] - vyc)
    de_goal = max(MANUAL['de_min'], min(MANUAL['de_max'], de_goal))
    dtz_goal = 0.35 + 2.0 * (MANUAL['vthr'] - frame['skor']) / MANUAL['vthr']
    if frame['vys'] < MANUAL['flare_h']:
        de_goal = max(de_goal, MANUAL['flare_de'])
    dtz_goal = max(0.0, min(MANUAL['dtz_max'], dtz_goal))
    _drive(out, state, 'de', de_goal, 'EV+', 'EV-')
    _drive(out, state, 'dtz', dtz_goal, 'TH+', 'TH-')

    if state['y_prev'] is not None and frame['t'] > state['t_prev']:
        dt = min(0.5, max(0.05, frame['t'] - state['t_prev']))
        vy_raw = (frame['y'] - state['y_prev']) / dt
        a = MANUAL['vy_alpha']
        state['vy'] = a * state['vy'] + (1.0 - a) * vy_raw
        # Точное решение WX'=a*DA-b*WX: при шаге 1 с метод Эйлера даёт
        # вдвое завышенную скорость крена и раскачивает контур.
        w_ss = MANUAL['roll_a'] / MANUAL['roll_b'] * state['da']
        state['w'] = w_ss + (state['w'] - w_ss) * math.exp(-MANUAL['roll_b'] * dt)
    state['y_prev'] = frame['y']
    state['t_prev'] = frame['t']
    da_goal = (-MANUAL['ky'] * frame['y'] - MANUAL['kvy'] * state['vy']
               - MANUAL['kw'] * state['w'])
    da_goal = max(MANUAL['da_min'], min(MANUAL['da_max'], da_goal))

    # Сигма-дельта по элеронам: команда AI меняет DA сразу на 0.05.
    # Накапливается ошибка между целью и уже поданным отклонением, поэтому
    # после импульса элероны возвращаются к нулю, не допуская стойкого крена.
    step = MANUAL['cmd_step']
    state['acc'] += 0.5 * (da_goal - state['da'])
    if state['acc'] >= step / 2 and state['da'] < MANUAL['da_max'] - 1e-6:
        out.append('AI+')
        state['da'] += step
        state['acc'] -= step
    elif state['acc'] <= -step / 2 and state['da'] > MANUAL['da_min'] + 1e-6:
        out.append('AI-')
        state['da'] -= step
        state['acc'] += step
    return out


def run_game_manual(ex, timeout=600):
    """Прогон с ручным пилотом в детерминированном пошаговом режиме STE.

    На каждое приглашение DISPAK отправляется ровно одна команда. Решение
    принимается один раз на кадр только после отработки группы шагов, поэтому
    результат не зависит от скорости вывода ОС.
    """
    answers = [str(ex['ktip']), '1', '0', '5', '0', str(ex['tmax']),
               str(ex['rseed']), str(ex['sigw']), str(ex['dt0'])]
    master, slave = pty.openpty()
    env = dict(os.environ)
    env['BESM6_PATH'] = str(Path.home() / '.besm6') + ':/usr/local/share/besm6'
    env['PATH'] = '/home/azizz/Yandex.Disk/rezerv/build/dispak:' + env.get('PATH', '')
    proc = subprocess.Popen(['dispak', '-p', 'GLCALL-2700.B6'], cwd=WORK,
                            stdin=slave, stdout=slave, stderr=slave,
                            env=env, close_fds=True)
    os.close(slave)
    buf = b''
    text = ''
    np = 0
    what = 0
    what_sent = 0
    sent = 0
    state = {'de': MANUAL['de_start'], 'dtz': MANUAL['dtz_start'], 'da': 0.0,
             'y_prev': None, 't_prev': None, 't_last': 0.0, 'decided': False,
             'vy': 0.0, 'w': 0.0, 'acc': 0.0}
    pending = collections.deque(answers)
    pending.extend(['STE'] * MANUAL['step_group'])
    steps = 0
    running = False
    finished = False
    deadline = time.time() + timeout
    with (WORK / (ex['id'] + '.log')).open('wb') as out:
        while time.time() < deadline:
            got = False
            # Сливаем весь доступный вывод: кадр АЦПУ крупный, и парциальные
            # чтения заставляют игру ждать освобождения буфера псевдотерминала.
            # Небольшая пауза, но без continue: если игра молчит, нужно
            # ответить на уже висящее приглашение.
            select.select([master], [], [], 0.005)
            while select.select([master], [], [], 0)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                out.write(chunk)
                before = text
                text += chunk.decode('utf-8', 'ignore')
                added = text[len(before):]
                ov = before[-3:]
                np += (ov + added).count('\n-\r') - ov.count('\n-\r')
                ov = before[-5:]
                what += (ov + added).count('WНАТ=') - ov.count('WНАТ=')
                got = True
            if got and what > 0 and what != what_sent:
                os.write(master, b'L0\n' if what_sent == 0 else b'\n')
                what_sent = what
            while np > sent and pending:
                cmd = pending.popleft()
                os.write(master, (cmd + '\n').encode())
                sent += 1
                if cmd == 'STE':
                    steps += 1
            if 'OCENKA=' in text and not finished:
                pending.clear()
                os.write(master, b'EXIT\n')
                finished = True
            if finished and not pending and 'КОНЕЦ ЗАДАЧИ' in text:
                break
            if (not finished and not running and not pending
                    and steps >= MANUAL['step_group']):
                frame = parse_frame(text)
                if frame:
                    state['t_last'] = frame['t']
                    if frame['vys'] <= 2.5:
                        pending.append('STA')
                        running = True
                    else:
                        pending.extend(manual_decision(frame, state))
                        pending.extend(['STE'] * MANUAL['step_group'])
                        steps = 0
            if 'КОНЕЦ ЗАДАЧИ' in text or proc.poll() is not None:
                break
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    os.close(master)
    text = buf.decode('utf-8', 'ignore').replace('Е', 'E')

    def last(pattern):
        m = re.findall(pattern, text)
        return float(m[-1]) if m else None

    sm = re.search(r'Б.ЛЛ=\s*([-\d.E+]+)', text)
    zm = re.search(r'Ч.T=\s*(\d)', text)
    vert = last(r'VERT=\s*([-\d.E+]+)')
    oce = last(r'OCENKA=\s*(\d+)')
    daln = last(r'DALN=\s*([-\d.E+]+)')
    return {'vert': vert, 'ocenka': int(oce) if oce is not None else None,
            'tch': -daln if daln is not None else None,
            'score': float(sm.group(1)) if sm else None,
            'zachet': int(zm.group(1)) if zm else None,
            'answers': sent, 'complete': 'OCENKA=' in text}


def run_game(ex, timeout=600, score=False):
    if ex.get('pilot') == 'manual':
        return run_game_manual(ex, timeout=timeout)
    answers = [str(ex['ktip']), '1', '0', '5', '0', str(ex['tmax']),
               str(ex['rseed']), str(ex['sigw']), str(ex['dt0']),
               'STA']
    if score:
        answers.append('SCR')
    answers.append('EXIT')
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
    finished = False
    deadline = time.time() + timeout
    with (WORK / (ex['id'] + '.log')).open('wb') as out:
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
    text = buf.decode('utf-8', 'ignore').replace('Е', 'E')

    def last(pattern):
        m = re.findall(pattern, text)
        return float(m[-1]) if m else None

    sm = re.search(r'Б.ЛЛ=\s*([-\d.E+]+)', text)
    zm = re.search(r'Ч.T=\s*(\d)', text)
    vert = last(r'VERT=\s*([-\d.E+]+)')
    oce = last(r'OCENKA=\s*(\d+)')
    daln = last(r'DALN=\s*([-\d.E+]+)')
    return {'vert': vert, 'ocenka': int(oce) if oce is not None else None,
            'tch': -daln if daln is not None else None,
            'score': float(sm.group(1)) if sm else None,
            'zachet': int(zm.group(1)) if zm else None,
            'answers': sent, 'complete': 'OCENKA=' in text}


def cmd_list(args):
    print('%-4s %-4s %-8s %-6s %-9s %s' % ('ID', '№', 'самолёт', 'SIGW', 'RSEED', 'название'))
    for e in load_all():
        print('%-4s %-4d %-8s %-6s %-9s %s' % (
            e['id'], e['number'], NAMES.get(e['ktip'], '?'),
            e['sigw'], e['rseed'], e['name']))


def cmd_show(args):
    print(json.dumps(find(args.key), ensure_ascii=False, indent=1))


def cmd_run(args):
    r = run_game(find(args.key))
    print(args.key, r)


def cmd_verify(args):
    exs = [find(args.key)] if args.key else load_all()
    ok = bad = 0
    for e in exs:
        r = run_game(e)
        g = e['goal']
        good = (r['vert'] is not None and r['vert'] <= g['max_vert'] and
                r['tch'] is not None and r['tch'] >= g['min_tch'] and
                r['ocenka'] is not None and r['ocenka'] <= g['max_ocenka'] and
                r['complete'])
        print('%-3s %s VERT=%s TCH=%s OCENKA=%s' % (
            e['id'], 'OK' if good else 'ЦЕЛЬ НЕ ДОСТИГНУТА',
            r['vert'], r['tch'], r['ocenka']))
        ok += good
        bad += not good
    print('итого: OK=%d, не достигнуто=%d' % (ok, bad))


def cmd_score(args):
    print('%-3s %-9s %-8s %-8s %s' % ('ID', 'самолёт', 'ОЦЕНКА', 'ЗАЧЁТ', 'балл'))
    passed = 0
    for e in load_all():
        r = run_game(e, score=True)
        z = r['zachet']
        print('%-3s %-9s %-8s %-8s %s' % (
            e['id'], NAMES.get(e['ktip'], '?'),
            r['ocenka'], 'да' if z == 1 else 'нет',
            r['score']))
        passed += z == 1
    print('итого: зачёт=%d из %d' % (passed, len(load_all())))


def cmd_report(args):
    lines = ['# УПРАЖНЕНИЯ ТРЕНАЖЁРА «ГЛИССАДА-6»', '',
             'Упражнения описаны в `TOOLS/exercises/*.json` и прогоняются',
             'в реальной игре: `python3 TOOLS/exercises.py verify`.', '',
             '| ID | Самолёт | SIGW | RSEED | Цель | Источник |',
             '|---|---|---|---|---|---|']
    for e in load_all():
        g = e['goal']
        lines.append('| %s | %s | %s | %s | VERT<=%s, TCH>=%s, OCENKA<=%s | %s |' % (
            e['id'], NAMES.get(e['ktip'], '?'), e['sigw'], e['rseed'],
            g['max_vert'], g['min_tch'], g['max_ocenka'], e['source']))
    out = REPO / 'docs' / 'analysis' / 'trenazher-exercises.md'
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('записано', out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    a = sub.add_parser('show'); a.add_argument('key')
    a = sub.add_parser('run'); a.add_argument('key')
    v = sub.add_parser('verify'); v.add_argument('key', nargs='?')
    sc = sub.add_parser('score'); sc.add_argument('key', nargs='?')
    sub.add_parser('report')
    args = ap.parse_args()
    {'list': cmd_list, 'show': cmd_show, 'run': cmd_run,
     'verify': cmd_verify, 'score': cmd_score, 'report': cmd_report}[args.cmd](args)


if __name__ == '__main__':
    main()
