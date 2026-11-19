#!/usr/bin/env python3
"""Сквозная проверка тренажёра «Глиссада-6» (этап 13 плана К-71).

Запускает все контрольные точки подряд и пишет Markdown-отчёт
`docs/analysis/etap13-integratsiya.md`. Никакого влияния на ядро игры:
только чтение и запуск существующих скриптов.

Использование:
  python3 TOOLS/final_verify.py
  python3 TOOLS/final_verify.py --report /tmp/itog.md
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# Задачи ПВС, которые обязаны исполняться на эмулируемой СМ-2.
TASKS = ('ps1', 'ps2', 'ps3', 'ps4', 'time', 'rcv', 'snd', 'rcd', 'wcd')


def run(cmd, timeout=600):
    """Выполнить команду, вернуть (код, вывод)."""
    try:
        proc = subprocess.run(cmd, cwd=REPO, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout)
        return proc.returncode, proc.stdout.decode('utf-8', 'ignore')
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b'').decode('utf-8', 'ignore')
        return 124, out + '\nПРЕВЫШЕН ТАЙМАУТ'


def check_pytest():
    code, out = run([sys.executable, '-m', 'pytest', 'TOOLS/tests', '-q'])
    ok = code == 0 and 'failed' not in out
    detail = next((ln for ln in out.splitlines() if 'passed' in ln), out[-200:])
    return ok, detail


def check_scenarios():
    code, out = run([sys.executable, 'TOOLS/calib/scenarios.py', 'verify'])
    ok = code == 0 and 'OK=10, отклонений=0' in out
    return ok, next((ln for ln in out.splitlines() if 'OK=' in ln), out[-200:])


def check_exercises():
    code, out = run([sys.executable, 'TOOLS/exercises.py', 'verify'])
    # 4/5 — зафиксированное состояние: упражнение T2 требует доработки
    # автопилота при SIGW>0 (GAP плана).
    ok = code == 0 and 'OK=4, не достигнуто=1' in out
    return ok, next((ln for ln in out.splitlines() if 'OK=' in ln), out[-200:])


def check_replay():
    code, out = run([sys.executable, 'TOOLS/replay.py', 'verify'])
    ok = code == 0 and 'СОВПАДЕНИЕ' in out and 'md1=' in out and 'md2=' in out
    detail = next((ln for ln in out.splitlines() if 'md1=' in ln), out[-200:])
    if ok:
        m1 = re.search(r'md1=([0-9a-f]+)', detail)
        m2 = re.search(r'md2=([0-9a-f]+)', detail)
        ok = bool(m1 and m2 and m1.group(1) == m2.group(1))
    return ok, detail


def check_sm2_tasks():
    lines = []
    ok_all = True
    for task in TASKS:
        src = HERE / 'sm2_tasks' / (task + '.asm')
        ini = Path('/tmp') / ('final-' + task + '.ini')
        if not src.exists():
            lines.append('%s: нет исходника' % task)
            ok_all = False
            continue
        c1, o1 = run([sys.executable, 'TOOLS/sm2asm.py', str(src), '-o', str(ini),
                      '--examine', 'RES' if task not in ('ps1', 'time', 'rcv', 'snd')
                      else {'ps1': 'OUT', 'time': 'TIME', 'rcv': 'NPACK',
                            'snd': 'RING'}[task]])
        if c1 != 0:
            lines.append('%s: ОШИБКА СБОРКИ: %s' % (task, o1.strip()[-120:]))
            ok_all = False
            continue
        c2, o2 = run([sys.executable, 'TOOLS/ps2_run.py', str(ini), '--timeout=60'])
        value = re.search(r'EXAMINE\s+\d+\s*=\s*([0-7]+)', o2)
        if c2 == 0 and value:
            lines.append('%s = %s' % (task, value.group(1)))
        else:
            lines.append('%s: нет результата' % task)
            ok_all = False
    return ok_all, '; '.join(lines)


def check_optional(script, args, marker):
    """Необязательная проверка этапа 11/12: отсутствие не считается ошибкой."""
    if not (HERE / script).exists():
        return None, 'модуль отсутствует'
    code, out = run([sys.executable, 'TOOLS/' + script] + args)
    ok = code == 0 and (marker in out if marker else True)
    detail = next((ln for ln in out.splitlines() if ln.strip()), out[-160:])
    return ok, detail[:160]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--report', default=str(REPO / 'docs/analysis/etap13-integratsiya.md'))
    args = ap.parse_args()

    started = time.strftime('%d.%m.%Y %H:%M:%S')
    checks = [
        ('Модульные тесты', check_pytest),
        ('Исторические сценарии (10/10)', check_scenarios),
        ('Упражнения (4/5)', check_exercises),
        ('Побайтовый повтор', check_replay),
        ('Задачи ПВС на СМ-2', check_sm2_tasks),
    ]
    results = []
    for name, fn in checks:
        print('ПРОВЕРКА: ' + name, flush=True)
        try:
            ok, detail = fn()
        except Exception as exc:
            ok, detail = False, '%s: %s' % (type(exc).__name__, exc)
        results.append((name, ok, detail))
        print('  ' + ('ГОТОВО' if ok else 'ОШИБКА') + ': ' + detail[:120], flush=True)

    optional = [
        ('Графика (этап 11)', 'graf_driver.py', ['verify'], 'СОВПАДЕНИЕ'),
        ('Звук (этап 12)', 'sound_adapter.py', ['demo'], ''),
        ('Платформа (этап 12)', 'platform_adapter.py', ['demo'], ''),
    ]
    for name, script, argv, marker in optional:
        ok, detail = check_optional(script, argv, marker)
        if ok is None:
            continue
        results.append((name, ok, detail))
        print('  ' + ('ГОТОВО' if ok else 'ОШИБКА') + ': ' + detail[:120], flush=True)

    good = sum(1 for _, ok, _ in results if ok)
    lines = ['# ИТОГОВАЯ ПРОВЕРКА ТРЕНАЖЁРА «ГЛИССАДА-6»', '',
             'Дата: ' + started + '.', '',
             '| Проверка | Результат | Деталь |', '|---|---|---|']
    for name, ok, detail in results:
        lines.append('| %s | %s | %s |' % (
            name, '✅' if ok else '❌', str(detail).replace('|', '/')))
    lines.append('')
    lines.append('Успешно: %d из %d.' % (good, len(results)))
    lines.append('')
    lines.append('ГAP: упражнение T2 не достигает целевой посадки при SIGW>0; '
                 'кодировка СМ-2 объявлена в `sm2_params.h`, не сверена с железом; '
                 'прямая связка `SM2KD` с сокетом отсутствует.'.replace('ГAP', 'GAP'))
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Отчёт: ' + str(report))
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
