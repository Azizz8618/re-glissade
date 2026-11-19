#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Хостовый прототип рельефа местности для тренажёра «Глиссада-6».

Модуль работает только на хосте и не изменяет ядро в каталоге ``SRC/``.
Он считает высоту земли по координатам ``X(11)`` (вдоль трассы) и ``X(12)``
(поперечное отклонение), просвет между самолётом и землёй и признак касания.
Значения ``X(11)``, ``X(12)`` и ``X(13)`` соответствуют регистратору
``GLRECF.FTN``: кадр ``RBUF`` хранит все тринадцать компонент вектора состояния.

Важно: числа профиля ниже — **условный учебный набор**, выбранный для
проверки алгоритма. В доступных исходниках и документах нет данных о
рельефе, высоте порога и препятствиях; это наша новая функция, а не
реконструкция. См. отчёт ``docs/analysis/relief-mestnosti.md``.

Запуск демонстрационного прогона:

    python3 TOOLS/terrain.py demo
    python3 TOOLS/terrain.py демо --point -1200 0 100
"""
from __future__ import annotations

import argparse
import math
import sys


# ---------------------------------------------------------------------------
# БЛОК ПАРАМЕТРОВ РЕЛЬЕФА.
# Все корректируемые числа собраны здесь, как блоки /SCPAR/, /RECPAR/
# и /TTXDAT/ в ядре. Менять профиль следует только в этом блоке.
# ---------------------------------------------------------------------------

# Продольный профиль: пары (X(11) в метрах, высота земли в метрах).
# X(11) отрицательно до порога, порог находится в нуле.
LONGITUDINAL_PROFILE = (
    (-15000.0, 0.0),
    (-6000.0, 0.0),
    (-3000.0, 18.0),
    (-2000.0, 65.0),
    (-1200.0, 95.0),
    (-700.0, 35.0),
    (-250.0, 4.0),
    (0.0, 0.0),
    (2500.0, -3.0),
)

# Поперечный профиль: пары (X(12) в метрах, добавка к высоте земли в метрах).
# Поправка складывается с продольным профилем; это упрощённый вариант
# двумерной модели, а не полноценная сетка высот.
LATERAL_PROFILE = (
    (-3000.0, 0.0),
    (-2350.0, 140.0),
    (-1700.0, 20.0),
    (-800.0, 0.0),
    (0.0, 0.0),
    (800.0, 0.0),
    (1700.0, 15.0),
    (3000.0, 25.0),
)

# Высота шасси HCR из ``SRC/GLTTX.FTN``, метры. Значение 2.5 выбрано
# как игровая калибровка для Ту-104 и Ан-2; в ядре HCR зависит от типа.
GEAR_HEIGHT = 2.5

# Демонстрационные состояния: (X(11), X(12), абсолютная высота X(13)).
DEMO_STATES = (
    (-15000.0, 0.0, 786.15),
    (-2350.0, -2350.0, 123.25),
    (-1200.0, 0.0, 100.0),
    (-200.0, 0.0, 10.0),
    (0.0, 0.0, 2.5),
)


class TerrainFormatError(ValueError):
    """Ошибка в задании профиля или координат: неверный формат или тип."""


def _is_number(raw: object) -> bool:
    """Проверить, что значение является конечным числом."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return False
    return math.isfinite(float(raw))


def _validate(points, label: str) -> tuple[tuple[float, float], ...]:
    """Проверить профиль и вернуть кортеж пар координата — высота."""
    if not points:
        raise TerrainFormatError('профиль ' + label + ' не может быть пустым')
    checked: list[tuple[float, float]] = []
    previous = None
    for item in points:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise TerrainFormatError(
                'точка профиля ' + label + ' должна парой из двух чисел')
        coord, height = item
        if not _is_number(coord) or not _is_number(height):
            raise TerrainFormatError(
                'координата и высота профиля ' + label + ' должны быть конечными числами')
        coord, height = float(coord), float(height)
        if previous is not None and coord <= previous:
            raise TerrainFormatError(
                'координаты профиля ' + label + ' должны возрастать')
        checked.append((coord, height))
        previous = coord
    return tuple(checked)


def _coordinate(raw: object, label: str) -> float:
    """Проверить числовую координату и вернуть число с плавающей точкой."""
    if not _is_number(raw):
        raise TerrainFormatError(label + ' должно быть конечным числом')
    return float(raw)


def _interpolate(points: tuple[tuple[float, float], ...], coord: float) -> float:
    """Линейно интерполировать профиль; вне диапазона взять крайнее значение."""
    if coord <= points[0][0]:
        return points[0][1]
    if coord >= points[-1][0]:
        return points[-1][1]
    for index in range(1, len(points)):
        left_x, left_h = points[index - 1]
        right_x, right_h = points[index]
        if coord <= right_x:
            share = (coord - left_x) / (right_x - left_x)
            return left_h + share * (right_h - left_h)
    return points[-1][1]


class TerrainProfile:
    """Кусочно-линейный рельеф по ``X(11)`` с поправкой по ``X(12)``.

    Конструктор принимает профили и высоту шасси. По умолчанию берутся
    параметры из блока констант в начале этого файла. Вне заданного диапазона
    координат высота равна соответствующему крайнему значению профиля.
    """

    def __init__(self, longitudinal=None, lateral=None, gear_height=None):
        self.longitudinal = _validate(
            LONGITUDINAL_PROFILE if longitudinal is None else longitudinal,
            'X(11)')
        self.lateral = _validate(
            LATERAL_PROFILE if lateral is None else lateral,
            'X(12)')
        if gear_height is None:
            gear_height = GEAR_HEIGHT
        self.gear_height = _coordinate(gear_height, 'высота шасси')
        if self.gear_height < 0.0:
            raise TerrainFormatError('высота шасси не может быть отрицательной')

    def elevation(self, x11, x12=0.0) -> float:
        """Вернуть высоту земли в метрах в точке ``X(11)``, ``X(12)``."""
        along = _interpolate(self.longitudinal, _coordinate(x11, 'X(11)'))
        across = _interpolate(self.lateral, _coordinate(x12, 'X(12)'))
        return along + across

    def clearance(self, x11, x12, altitude) -> float:
        """Вернуть просвет в метрах: абсолютная высота минус высота земли."""
        ground = self.elevation(x11, x12)
        return _coordinate(altitude, 'высота X(13)') - ground

    def touchdown(self, x11, x12, altitude) -> bool:
        """Признак касания: просвет не больше высоты шасси HCR."""
        return self.clearance(x11, x12, altitude) <= self.gear_height

    def profile_points(self) -> list[dict]:
        """Вернуть копию узлов продольного профиля для таблицы и печати."""
        return [
            {'x11': coord, 'elevation': height}
            for coord, height in self.longitudinal
        ]


def run_demo(log=print, point=None) -> int:
    """Напечатать профиль и примеры расчёта; вернуть нулевой код завершения."""
    terrain = TerrainProfile()
    log('ДЕМОНСТРАЦИЯ РЕЛЬЕФА МЕСТНОСТИ')
    log('ПРОДОЛЬНЫЙ ПРОФИЛЬ (ВДОЛЬ ТРАССЫ)')
    log('{:>10} {:>16}'.format('X(11), М', 'ЗЕМЛЯ, М'))
    for row in terrain.profile_points():
        log('{:>10.1f} {:>16.1f}'.format(row['x11'], row['elevation']))
    log('ПОПЕРЕЧНЫЙ ПРОФИЛЬ (ПОПРАВКА К ВЫСОТЕ ЗЕМЛИ)')
    log('{:>10} {:>16}'.format('X(12), М', 'ПОПРАВКА, М'))
    for coord, height in terrain.lateral:
        log('{:>10.1f} {:>16.1f}'.format(coord, height))
    log('ПРИМЕРЫ РАСЧЁТА')
    states = list(DEMO_STATES)
    if point is not None:
        states = [tuple(point)]
    for x11, x12, altitude in states:
        ground = terrain.elevation(x11, x12)
        gap = terrain.clearance(x11, x12, altitude)
        contact = 'ДА' if terrain.touchdown(x11, x12, altitude) else 'НЕТ'
        log('X(11)={:>9.1f} X(12)={:>8.1f} ВЫСОТА={:>8.1f} '
            'ЗЕМЛЯ={:>8.1f} ПРОСВЕТ={:>8.1f} КАСАНИЕ={}'.format(
                x11, x12, altitude, ground, gap, contact))
    log('ВЫСОТА ШАССИ HCR={:.1f} М'.format(terrain.gear_height))
    log('ПРОФИЛЬ УСЛОВНЫЙ: ЭТО ПРОТОТИП, НЕ РЕКОНСТРУКЦИЯ ИСТОЧНИКОВ')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    demo = sub.add_parser('demo', aliases=['демо'],
                          help='печать таблицы профиля и примера расчёта')
    demo.add_argument('--point', '--точка', dest='point', nargs=3,
                      type=float, metavar=('X11', 'X12', 'ВЫСОТА'),
                      help='добавить расчёт для заданной точки')
    args = parser.parse_args(argv)
    try:
        return run_demo(point=args.point)
    except TerrainFormatError as exc:
        print('ОШИБКА: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
