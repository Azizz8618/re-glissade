#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Внешний адаптер подвижной платформы тренажёра «Глиссада-6» (этап 12).

Модуль работает только на хосте. Он берёт состояние, которое игра пишет
в регистраторе ``GLRECF.FTN`` (кадры ``X(13), U(4), T``), и по явным
коэффициентам превращает его в команды движения платформы по трём осям:
тангаж, крен и вертикальное перемещение. Величины ограничены заранее
заданными пределах. Никаких внешних библиотек, портов и покупателей
команд на ядре нет: результат — обычный файл в формате JSON.

Как и в К-71, двигательная периферия не является частью модели:
исходники в каталоге ``SRC/`` этот модуль не изменяет.

Запуск демонстрационного прогона:

    python3 TOOLS/platform_adapter.py demo
    python3 TOOLS/platform_adapter.py демо --out /tmp/мой-прогон.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Блок настроек адаптера. Как и блоки /SCPAR/, /RECPAR/, /FAULT/ в ядре,
# пределы и коэффициенты собраны здесь, а не внутри методов.
# ---------------------------------------------------------------------------

PLATFORM_LIMITS = {
    'pitch_deg': 8.0,    # тангаж, градусы
    'roll_deg': 12.0,    # крен, градусы
    'heave_m': 0.30,     # вертикальное перемещение, метры
}

PLATFORM_GAINS = {
    'pitch_per_g': 4.0,       # тангаж за единицу перегрузки сверх единицы
    'pitch_per_vert': 0.6,    # тангаж за метр в секунду вертикальной скорости
    'pitch_per_speed': 0.05,  # тангаж за метр в секунду отклонения скорости
    'pitch_per_ctrl': 2.0,    # тангаж за единицу ручки руля высоты
    'roll_per_ctrl': 8.0,     # крен за единицу ручки элеронов
    'heave_per_vert': 0.04,   # перемещение за метр в секунду вертикальной скорости
    'heave_per_g': 0.05,      # перемещение за единицу перегрузки сверх единицы
}

REFERENCE_SPEED = 70.0   # опорная горизонтальная скорость, метры в секунду
REFERENCE_G = 1.0        # перегрузка при горизонтальном полёте

# Подписи осей для журнала и файла команд.
AXIS_LABELS = {
    'pitch': 'тангаж',
    'roll': 'крен',
    'heave': 'вертикальное перемещение',
}

AXIS_UNITS = {
    'pitch': 'градус',
    'roll': 'градус',
    'heave': 'метр',
}

# Синтетические состояния для демонстрационного прогона.
# Поля vert, speed и g_load заданы в единицах, перечисленных выше;
# команды рулей заданы в долях от полного отклонения.
DEMO_STATES = [
    {'vert': 0.0, 'speed': 70.0, 'g_load': 1.0,
     'controls': {'pitch': 0.0, 'roll': 0.0}},
    {'vert': -1.5, 'speed': 66.0, 'g_load': 1.2,
     'controls': {'pitch': 0.4, 'roll': -0.3}},
    {'vert': 3.0, 'speed': 62.0, 'g_load': 2.4,
     'controls': {'pitch': 1.0, 'roll': 0.9}},
    {'vert': 0.2, 'speed': 58.0, 'g_load': 1.0,
     'controls': {'pitch': 0.0, 'roll': 0.0}},
]

DEFAULT_DEMO_PATH = Path('/tmp') / 'etap12-platforma-demo.json'


class StateFormatError(ValueError):
    """Ошибка в описании состояния: неверное поле или его тип."""


def clamp(value: float, limit: float) -> float:
    """Ограничить число в заданных пределах по модулю."""
    return max(-limit, min(limit, value))


def _number(raw: object, field: str) -> float:
    """Проверить числовое поле состояния и вернуть число с плавающей точкой."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise StateFormatError('поле ' + field + ' должно быть числом')
    value = float(raw)
    if not math_isfinite(value):
        raise StateFormatError('поле ' + field + ' должно быть конечным числом')
    return value


def math_isfinite(value: float) -> bool:
    """Проверить число на бесконечность и неопределённость."""
    return value == value and value not in (float('inf'), float('-inf'))


def parse_state(raw: object) -> dict:
    """Проверить описание состояния и привести команды рулей к единому виду."""
    if not isinstance(raw, dict):
        raise StateFormatError('состояние должно быть объектом')
    required = ('vert', 'speed', 'g_load', 'controls')
    for field in required:
        if field not in raw:
            raise StateFormatError('в состоянии нет поля ' + field)
    controls = raw['controls']
    if isinstance(controls, (list, tuple)):
        if len(controls) < 2:
            raise StateFormatError('в списке команд рулей нужно два значения')
        pitch_ctrl, roll_ctrl = controls[0], controls[1]
    elif isinstance(controls, dict):
        if 'pitch' not in controls or 'roll' not in controls:
            raise StateFormatError('в командах рулей нужны поля pitch и roll')
        pitch_ctrl, roll_ctrl = controls['pitch'], controls['roll']
    else:
        raise StateFormatError('команды рулей должны быть объектом или списком')
    return {
        'vert': _number(raw['vert'], 'vert'),
        'speed': _number(raw['speed'], 'speed'),
        'g_load': _number(raw['g_load'], 'g_load'),
        'controls': {
            'pitch': clamp(_number(pitch_ctrl, 'руль высоты'), 1.0),
            'roll': clamp(_number(roll_ctrl, 'элероны'), 1.0),
        },
    }


class PlatformAdapter:
    """Отображение состояния полёта в команды подвижной платформы."""

    def __init__(self, limits: dict | None = None, gains: dict | None = None):
        self.limits = dict(PLATFORM_LIMITS if limits is None else limits)
        self.gains = dict(PLATFORM_GAINS if gains is None else gains)
        for axis in ('pitch', 'roll', 'heave'):
            key = axis + ('_m' if axis == 'heave' else '_deg')
            if self.limits.get(key, 0.0) <= 0:
                raise StateFormatError('предел по оси ' + axis + ' должен быть положительным')

    def commands(self, state: dict) -> list[dict]:
        """Вернуть список команд по трём осям с учётом ограничений."""
        data = parse_state(state)
        g = self.gains
        excess_g = data['g_load'] - REFERENCE_G
        speed_error = data['speed'] - REFERENCE_SPEED
        pitch = (
            g['pitch_per_g'] * excess_g
            + g['pitch_per_vert'] * data['vert']
            + g['pitch_per_speed'] * speed_error
            + g['pitch_per_ctrl'] * data['controls']['pitch']
        )
        roll = g['roll_per_ctrl'] * data['controls']['roll']
        heave = (
            g['heave_per_vert'] * data['vert']
            + g['heave_per_g'] * excess_g
        )
        values = (
            ('pitch', pitch, self.limits['pitch_deg']),
            ('roll', roll, self.limits['roll_deg']),
            ('heave', heave, self.limits['heave_m']),
        )
        return [
            {
                'axis': axis,
                'label': AXIS_LABELS[axis],
                'value': round(clamp(raw, limit), 4),
                'unit': AXIS_UNITS[axis],
                'limit': round(limit, 4),
            }
            for axis, raw, limit in values
        ]

    def write_json(self, commands: list[dict], path) -> str:
        """Сохранить команды в файл формата JSON и вернуть путь."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(commands, ensure_ascii=False, indent=2) + '\n',
                          encoding='utf-8')
        return str(target)


def run_demo(out=None, log=print) -> str:
    """Прогнать синтетические состояния, напечатать и сохранить команды."""
    adapter = PlatformAdapter()
    records = []
    for number, state in enumerate(DEMO_STATES, 1):
        commands = adapter.commands(state)
        for command in commands:
            records.append({'frame': number, **command})
        log('КАДР {}: {}'.format(number, ' '.join(
            '{} = {:+.3f} {}'.format(item['label'], item['value'], item['unit'])
            for item in commands)))
    target = Path(out) if out is not None else DEFAULT_DEMO_PATH
    written = adapter.write_json(records, target)
    log('КОМАНД: {}'.format(len(records)))
    log('ФАЙЛ: ' + written)
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    demo = sub.add_parser('demo', aliases=['демо'],
                          help='прогон на синтетическом состоянии')
    demo.add_argument('--out', metavar='ФАЙЛ',
                      help='куда записать файл формата JSON')
    args = parser.parse_args(argv)
    try:
        run_demo(args.out)
    except (StateFormatError, OSError) as exc:
        print('ОШИБКА: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
