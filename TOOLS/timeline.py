#!/usr/bin/env python3
"""Драйвер масштабов времени для задач ПВС на СМ-2 (этап Q5).

Идея: хост задаёт темп, а эмулятор СМ-2 исполняет задачу по одному
шагу. На каждой границе шага доставляется событие (кадр DKS PING
через `sm2_dks_bridge`) и пишется лог «модельное время / стенное
время / задержка». Это organizational принцип К-71: событие
доставляется задаче-получателю, а не просто печатается.

Использование:
  python3 TOOLS/timeline.py --ticks 10 --scale 1
  python3 TOOLS/timeline.py --ticks 10 --scale 10 --event

Масштаб 1 — одна модельная секунда за стенную, 10 — ускорение в 10 раз,
0,1 — замедление в 10 раз. Шаг модели фиксирован 0,1 с.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRIDGE = HERE / 'sm2_dks_bridge.py'


def load_bridge():
    spec = importlib.util.spec_from_file_location('sm2_dks_bridge', BRIDGE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['sm2_dks_bridge'] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ticks', type=int, default=10, help='число шагов модели')
    ap.add_argument('--scale', type=float, default=1.0,
                    help='масштаб: 1 — реальное время, 10 — ускорение')
    ap.add_argument('--event', action='store_true',
                    help='посылать кадр DKS PING на каждой границе')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=4140)
    ap.add_argument('--log', default='/tmp/timeline-sm2.log')
    args = ap.parse_args()

    if args.scale <= 0:
        print('СТОП: масштаб должен быть положительным', file=sys.stderr)
        return 2

    step = 0.1                      # модельный шаг, с
    frame_log = []
    bridge = load_bridge() if args.event else None
    link = None
    if bridge is not None:
        try:
            link = bridge.DksLink(host=args.host, port=args.port,
                                  log=frame_log.append).connect()
        except Exception as exc:
            print('Предупреждение: сервер DKS недоступен (%s); события не идут' % exc,
                  file=sys.stderr)
            link = None

    rows = []
    wall0 = time.monotonic()
    for k in range(args.ticks):
        model_t = (k + 1) * step
        target = wall0 + model_t / args.scale
        now = time.monotonic()
        if target > now:
            time.sleep(target - now)
        sent = ''
        if link is not None:
            try:
                response = link.ping()
                sent = response.describe_reply()
            except Exception as exc:
                sent = 'ОШИБКА ' + str(exc)
        wall_t = time.monotonic() - wall0
        latency = wall_t - model_t / args.scale
        row = (k + 1, model_t, wall_t, latency, sent)
        rows.append(row)
        print('шаг=%d модель=%6.2f стенное=%8.4f задержка=%+8.4f событие=%s' % row)

    lines = ['шаг=%d модель=%.3f стенное=%.6f задержка=%.6f событие=%s' % r
             for r in rows]
    if frame_log:
        lines.append('--- кадры DKS ---')
        lines.extend(frame_log)
    Path(args.log).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if link is not None:
        link.close()
    print('Лог: ' + args.log)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
