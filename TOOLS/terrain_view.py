#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Показ поля рельефа по потоку телеметрии тренажёра «Глиссада-6».

Модуль читает вывод команды ``RPL`` регистратора ``GLRECF.FTN`` и строит
текстовый кадр: линию рельефа, глиссаду, отметку самолёта, порог взлётно-
посадочной полосы и подпись текущего и минимального просвета. Он работает
только на хосте, не меняет ядро и не влияет на побайтовый повтор телеметрии.

Формат строк берётся из ``SRC/GLDIAL.PAS:322-328``: после строки ``TELE``
идут три строки ``X`` и одна строка ``U``. Числа печатаются в научной записи
подряд без разделителей, причём ширина поля плавающая. Поэтому разбор
выполняется регулярным выражением, а не нарезкой на фиксированные столбцы.
Ограничение: из тринадцати компонент нас интересуют только путь ``X(11)``,
боковое отклонение ``X(12)``, высота ``X(13)`` и модельное время ``T``.

Запуск:

    python3 TOOLS/terrain_view.py --telemetry TOOLS/replays/tu104-cal.json
    python3 TOOLS/terrain_view.py --demo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import terrain as tr

# Регулярное выражение для числа в научной записи вида 7.6490E+01.
# Буква D в экспоненте допускается как запасной вариант.
SCIENTIFIC = re.compile(r'[+-]?(?:\d+\.\d+|\d+|\.\d+)[EeDd][+-]?\d+')
TELE_LINE = re.compile(
    r'^TELE\s+(\d+)\s+T=\s*([+-]?(?:\d+\.\d+|\d+|\.\d+)[EeDd][+-]?\d+)')


def _clean(line):
    """Убрать возможный префикс эха терминала из строки."""
    return line[2:] if line.startswith('> ') else line


def _number(token):
    """Преобразовать число научной записи к типу с плавающей точкой."""
    return float(token.replace('D', 'E').replace('d', 'e'))


def parse_telemetry(lines):
    """Разобрать поток ``RPL`` и вернуть список кадров.

    На входе — последовательность строк или один текст с переводами строк.
    Каждый результат содержит поля ``index``, ``time``, ``x11``, ``x12``,
    ``alt``, а также полный набор ``x`` и ``u``. Строки ``FRAMES``, ``EV``
    и прочий вывод игнорируются.
    """
    if isinstance(lines, str):
        lines = lines.splitlines()
    rows = [_clean(str(line)) for line in lines]
    frames = []
    position = 0
    while position < len(rows):
        match = TELE_LINE.match(rows[position].strip())
        if match is None:
            position += 1
            continue
        index = int(match.group(1))
        time = _number(match.group(2))
        numbers = []
        cursor = position + 1
        while cursor < len(rows) and len(numbers) < 13:
            stripped = rows[cursor].strip()
            if stripped.startswith('TELE') or stripped.startswith('EV '):
                break
            numbers.extend(SCIENTIFIC.findall(rows[cursor]))
            cursor += 1
        if len(numbers) < 13:
            position += 1
            continue
        x_values = [_number(token) for token in numbers[:13]]
        u_values = []
        if cursor < len(rows) and rows[cursor].strip().startswith('U='):
            u_values = [_number(token) for token in SCIENTIFIC.findall(rows[cursor])]
            cursor += 1
        frames.append({
            'index': index,
            'time': time,
            'x': x_values,
            'u': u_values,
            'x11': x_values[10],
            'x12': x_values[11],
            'alt': x_values[12],
        })
        position = cursor
    return frames


def load_frames(source):
    """Загрузить кадры из JSON-эталона, текстового лога или готового списка."""
    if isinstance(source, (list, tuple)):
        if source and isinstance(source[0], dict) and 'x11' in source[0]:
            return list(source)
        return parse_telemetry(source)
    path = Path(source)
    text = path.read_text(encoding='utf-8')
    if path.suffix.lower() == '.json':
        data = json.loads(text)
        if isinstance(data, dict) and 'telemetry' in data:
            return parse_telemetry(data['telemetry'])
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return list(data)
        raise ValueError('в JSON нет поля telemetry со строками регистратора')
    return parse_telemetry(text)


def _make_canvas(width, height):
    """Создать пустое поле заданного размера."""
    return [[' '] * width for _ in range(height)]


def _axis(width, height, top, bottom):
    """Подписать шкалу высоты слева от поля."""
    labels = []
    for row in range(height):
        value = top - row * (top - bottom) / max(1, height - 1)
        labels.append('{:>6.0f} |'.format(value))
    return labels


def render_field(frames, terrain=None, monitor=None, width=60, height=14,
                 frame_index=None):
    """Построить текстовый кадр поля по списку кадров телеметрии.

    Возвращает список строк. Внутри поля обозначения: ``#`` — земля,
    ``.`` — глиссада, ``*`` — самолёт, ``|`` — порог полосы. Подпись содержит
    текущий и минимальный просвет. Аргумент ``frame_index`` задаёт номер
    показываемого кадра; по умолчанию берётся последний.
    """
    if terrain is None:
        terrain = tr.TerrainProfile()
    if not frames:
        return ['НЕТ КАДРОВ ТЕЛЕМЕТРИИ']
    if width < 20 or height < 6:
        raise ValueError('размер поля слишком мал: ширина от 20, высота от 6')
    if frame_index is not None and frame_index < 0:
        raise ValueError('номер кадра не может быть отрицательным')
    current = len(frames) - 1 if frame_index is None else frame_index
    if current >= len(frames):
        raise ValueError('такого номера кадра нет')
    current_frame = frames[current]

    x_values = [frame['x11'] for frame in frames]
    x_min = min([terrain.longitudinal[0][0]] + x_values)
    x_max = max([0.0, terrain.longitudinal[-1][0]] + x_values)
    if x_max - x_min < 1.0:
        x_max = x_min + 1.0

    samples = [x_min + (x_max - x_min) * i / (width - 1)
               for i in range(width)]
    elevations = [terrain.elevation(x, current_frame['x12']) for x in samples]
    alts = ([frame['alt'] for frame in frames] + elevations +
            [-tr.GLIDE_SLOPE * x_min, 0.0])
    top = max(alts) + max(10.0, 0.05 * abs(max(alts)))
    bottom = min(min(alts), 0.0) - 10.0

    def column(x11):
        return max(0, min(width - 1,
                          round((x11 - x_min) / (x_max - x_min) * (width - 1))))

    def row(altitude):
        return max(0, min(height - 1,
                          round((top - altitude) / (top - bottom) * (height - 1))))

    canvas = _make_canvas(width, height)
    for col, x11 in enumerate(samples):
        glide_alt = -tr.GLIDE_SLOPE * x11
        canvas[row(glide_alt)][col] = '.'
    for col, elevation in enumerate(elevations):
        for line in range(row(elevation), height):
            canvas[line][col] = '#'
    threshold_col = column(0.0)
    for line in range(height):
        canvas[line][threshold_col] = '|'
    canvas[row(current_frame['alt'])][column(current_frame['x11'])] = '*'

    current_gap = terrain.clearance(
        current_frame['x11'], current_frame['x12'], current_frame['alt'])
    if monitor is not None and monitor.samples:
        minimum = monitor.min_clearance
    else:
        minimum = min(terrain.clearance(frame['x11'], frame['x12'], frame['alt'])
                      for frame in frames)

    lines = ['КАДР {:>3} ВРЕМЯ {:>6.1f} С  X(11)={:>8.0f} М  '
             'X(12)={:>7.1f} М  ВЫСОТА={:>7.1f} М'.format(
                 current_frame['index'], current_frame['time'],
                 current_frame['x11'], current_frame['x12'],
                 current_frame['alt'])]
    for label, painted in zip(_axis(width, height, top, bottom), canvas):
        lines.append(label + ''.join(painted))
    lines.append('       +' + '-' * width)
    distance_label = ('{:.0f} КМ'.format(x_min / 1000.0)).ljust(
        max(0, column(0.0) - 9)) + 'ПОРОГ ВПП'
    lines.append('       ' + distance_label)
    lines.append('УСЛОВИЯ: ./ТОЧКИ - ГЛИССАДА, # - ЗЕМЛЯ, '
                 '* - САМОЛЁТ, | - ПОРОГ ВПП')
    lines.append('УКЛОН ГЛИССАДЫ {:.5f}; ЗЕМЛЯ ПО X(12)={:.0f} М'.format(
        tr.GLIDE_SLOPE, current_frame['x12']))
    lines.append('ПРОСВЕТ СЕЙЧАС = {:>7.1f} М; МИНИМАЛЬНЫЙ = {:>7.1f} М'.format(
        current_gap, minimum))
    if monitor is not None:
        lines.append('ЗАМЕРОВ = {}; СОБЫТИЙ = {}'.format(
            monitor.samples, len(monitor.events)))
        if monitor.events:
            last = monitor.events[-1]
            lines.append('ПОСЛЕДНЕЕ СОБЫТИЕ: {} ВРЕМЯ {:>6.1f} С '
                         'ПРОСВЕТ {:>7.1f} М'.format(
                             last['level'], last['time'] or 0.0,
                             last['clearance']))
    return lines


def demo_frames():
    """Собрать синтетические кадры для демонстрации без чтения файлов."""
    frames = []
    for index, (x11, x12, altitude) in enumerate(tr.DEMO_STATES):
        frames.append({
            'index': index + 1,
            'time': index * 5.0,
            'x11': x11, 'x12': x12, 'alt': altitude,
            'x': [0.0] * 10 + [x11, x12, altitude],
            'u': [0.0] * 4,
        })
    return frames


def run_show(source, width=60, height=14, frame_index=None):
    """Загрузить кадры, пропустить их через монитор и вернуть строки кадра."""
    frames = load_frames(source)
    if not frames:
        return ['НЕТ КАДРОВ ТЕЛЕМЕТРИИ']
    monitor = tr.ClearanceMonitor()
    for frame in frames:
        monitor.observe(frame['x11'], frame['x12'], frame['alt'],
                        time=frame['time'])
    return render_field(frames, monitor=monitor, width=width, height=height,
                        frame_index=frame_index)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--telemetry', '--telemetriya', dest='telemetry',
                        help='путь к JSON-эталону или текстовому логу')
    parser.add_argument('--demo', action='store_true',
                        help='показать синтетический пример')
    parser.add_argument('--width', type=int, default=60,
                        help='ширина поля в символах')
    parser.add_argument('--height', type=int, default=14,
                        help='высота поля в строках')
    parser.add_argument('--frame', type=int, default=None,
                        help='номер показываемого кадра')
    args = parser.parse_args(argv)
    if not args.telemetry and not args.demo:
        parser.error('нужен ключ --telemetry или --demo')
    try:
        source = demo_frames() if args.demo else args.telemetry
        for line in run_show(source, width=args.width, height=args.height,
                             frame_index=args.frame):
            print(line)
    except (OSError, ValueError, json.JSONDecodeError, tr.TerrainFormatError) as exc:
        print('ОШИБКА: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
