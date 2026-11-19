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

Кроме расчёта в одной точке модуль содержит анализ пройденного отрезка
и монитор просвета. Это хостовой слой: он показывает и фиксирует опасное
сближение, но не предотвращает его и не меняет траекторию в ядре.

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

# Уклон глиссады из ``SRC/GLMAIN.FTN:88``: отклонение
# EGLI = X(13) + 0.05241 * X(11). Используется только хостовым рендером.
GLIDE_SLOPE = 0.05241

# --- ПАРАМЕТРЫ АНАЛИЗА ПРОЙДЕННОГО ОТРЕЗКА. ---
# Шаг модели 0,1 с при скорости около 70 метров в секунду даёт 7 метров
# пути между кадрами. Чтобы не пропустить узкое препятствие, отрезок между
# соседними кадрами дробится на части не длиннее этой величины. дополнительно
# проверяются узлы профиля, попавшие внутрь отрезка.
SEGMENT_STEP_LIMIT_M = 7.0
SEGMENT_EPSILON = 1e-9

# --- ПОРОГИ ПРЕДУПРЕЖДЕНИЯ (НЕ КАЛИБРОВАНЫ). ---
# Чисел в исходниках нет: это учебные пороги хостового монитора.
WARNING_CLEARANCE_M = 30.0
CRITICAL_CLEARANCE_M = 10.0
WARNING_VERTICAL_SPEED_MPS = -3.0

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


def _segment_geometry(x11_0, x12_0, altitude_0, x11_1, x12_1, altitude_1):
    """Проверить концы отрезка и вернуть точку начала, приращения и длину."""
    start = (
        _coordinate(x11_0, 'X(11) начала отрезка'),
        _coordinate(x12_0, 'X(12) начала отрезка'),
        _coordinate(altitude_0, 'высоты начала отрезка'),
    )
    finish = (
        _coordinate(x11_1, 'X(11) конца отрезка'),
        _coordinate(x12_1, 'X(12) конца отрезка'),
        _coordinate(altitude_1, 'высоты конца отрезка'),
    )
    delta = tuple(finish[i] - start[i] for i in range(3))
    length = math.sqrt(sum(component * component for component in delta))
    return start, delta, length


def _segment_fractions(start, delta, length, terrain):
    """Собрать доли отрезка: равномерная сетка и узлы профиля внутри отрезка."""
    steps = max(1, int(math.ceil(length / SEGMENT_STEP_LIMIT_M - SEGMENT_EPSILON)))
    fractions = {float(index) / steps for index in range(steps + 1)}
    for offset, axis in ((0, terrain.longitudinal), (1, terrain.lateral)):
        span = delta[offset]
        if abs(span) < SEGMENT_EPSILON:
            continue
        for coord, _height in axis:
            share = (coord - start[offset]) / span
            if SEGMENT_EPSILON < share < 1.0 - SEGMENT_EPSILON:
                fractions.add(share)
    return sorted(fractions)


def _point_on_segment(start, delta, share):
    """Вернуть координаты точки отрезка по его доле."""
    return tuple(start[i] + share * delta[i] for i in range(3))


def _contact_record(share, start, delta, terrain):
    """Собрать описание касания в точке отрезка."""
    x11, x12, altitude = _point_on_segment(start, delta, share)
    ground = terrain.elevation(x11, x12)
    return {
        'x11': x11,
        'x12': x12,
        'altitude': altitude,
        'ground': ground,
        'clearance': altitude - ground,
        'distance': share * math.sqrt(sum(component * component for component in delta)),
        'fraction': share,
    }


def collision_along_segment(x11_0, x12_0, altitude_0,
                            x11_1, x12_1, altitude_1,
                            terrain=None):
    """Найти первое касание земли на всём отрезке между двумя кадрами.

    Аргументы задают начало и конец отрезка в координатах ``X(11)``, ``X(12)``
    и ``X(13)``. Отрезок проверяется с шагом не более ``SEGMENT_STEP_LIMIT_M``
    метров пути; дополнительно проверяются узлы профиля внутри отрезка, чтобы
    не перескочить узкое препятствие. Граница касания уточняется делением
    отрезка пополам. Признак касания совпадает с ядром: просвет не больше
    высоты шасси.

    Возвращает словарь с полями ``x11``, ``x12``, ``altitude``, ``ground``,
    ``clearance``, ``distance`` и ``fraction`` либо ``None``, если касания нет.
    Необязательный аргумент ``terrain`` позволяет передать другой профиль.
    """
    if terrain is None:
        terrain = TerrainProfile()
    start, delta, length = _segment_geometry(
        x11_0, x12_0, altitude_0, x11_1, x12_1, altitude_1)
    fractions = _segment_fractions(start, delta, length, terrain)
    limit = terrain.gear_height

    def gap_at(share):
        x11, x12, altitude = _point_on_segment(start, delta, share)
        return altitude - terrain.elevation(x11, x12)

    previous = fractions[0]
    if gap_at(previous) <= limit + SEGMENT_EPSILON:
        return _contact_record(previous, start, delta, terrain)
    for share in fractions[1:]:
        if gap_at(share) <= limit + SEGMENT_EPSILON:
            low, high = previous, share
            for _ in range(40):
                middle = (low + high) / 2.0
                if gap_at(middle) <= limit + SEGMENT_EPSILON:
                    high = middle
                else:
                    low = middle
            return _contact_record(high, start, delta, terrain)
        previous = share
    return None


class ClearanceMonitor:
    """Накопление минимального просвета и событий опасного сближения.

    Монитор не влияет на траекторию: он только наблюдает кадры через методы
    ``observe`` и ``observe_segment``. Событие записывается при входе в зону
    опасности, чтобы не дублировать предупреждение на каждом кадре. Пороги
    задаются в конструкторе, по умолчанию берутся из блока констант.
    """

    def __init__(self, terrain=None, warning_clearance=None,
                 critical_clearance=None, warning_vertical_speed=None):
        self.terrain = TerrainProfile() if terrain is None else terrain
        self.warning_clearance = (
            WARNING_CLEARANCE_M if warning_clearance is None
            else _coordinate(warning_clearance, 'порог предупреждения'))
        self.critical_clearance = (
            CRITICAL_CLEARANCE_M if critical_clearance is None
            else _coordinate(critical_clearance, 'критический порог'))
        self.warning_vertical_speed = (
            WARNING_VERTICAL_SPEED_MPS if warning_vertical_speed is None
            else _coordinate(warning_vertical_speed, 'порог вертикальной скорости'))
        self.reset()

    def reset(self):
        """Очистить накопленные данные монитора."""
        self.min_clearance = math.inf
        self.min_point = None
        self.events = []
        self.samples = 0
        self._alarm = False
        self._previous = None

    def _inferred_vertical_speed(self, altitude, time):
        if self._previous is None:
            return None
        previous_time, previous_altitude = self._previous
        if time is None or previous_time is None:
            return None
        interval = time - previous_time
        if interval <= 0.0:
            return None
        return (altitude - previous_altitude) / interval

    def observe(self, x11, x12, altitude, time=None, vertical_speed=None):
        """Зарегистрировать один кадр и вернуть описание наблюдения."""
        x11 = _coordinate(x11, 'X(11)')
        x12 = _coordinate(x12, 'X(12)')
        altitude = _coordinate(altitude, 'высота X(13)')
        ground = self.terrain.elevation(x11, x12)
        clearance = altitude - ground
        self.samples += 1
        if clearance < self.min_clearance:
            self.min_clearance = clearance
            self.min_point = {
                'x11': x11, 'x12': x12, 'altitude': altitude,
                'ground': ground, 'clearance': clearance, 'time': time,
            }
        speed = (vertical_speed if vertical_speed is not None
                 else self._inferred_vertical_speed(altitude, time))
        dangerous = (clearance < self.warning_clearance and
                     (speed is None or speed <= self.warning_vertical_speed))
        if dangerous and not self._alarm:
            level = ('КРИТИЧНО' if clearance <= self.critical_clearance
                     else 'ПРЕДУПРЕЖДЕНИЕ')
            self.events.append({
                'time': time, 'level': level, 'clearance': clearance,
                'vertical_speed': speed, 'x11': x11, 'x12': x12,
                'altitude': altitude,
            })
        self._alarm = dangerous
        self._previous = (time, altitude)
        return {
            'x11': x11, 'x12': x12, 'altitude': altitude,
            'ground': ground, 'clearance': clearance,
            'vertical_speed': speed, 'time': time,
        }

    def observe_segment(self, x11_0, x12_0, altitude_0,
                        x11_1, x12_1, altitude_1,
                        time_0=None, time_1=None):
        """Пропустить через монитор весь отрезок между кадрами.

        Возвращает результат ``collision_along_segment`` для того же отрезка.
        Промежуточные точки получают модельное время линейной интерполяцией,
        вертикальная скорость считается по концам отрезка.
        """
        collision = collision_along_segment(
            x11_0, x12_0, altitude_0, x11_1, x12_1, altitude_1,
            terrain=self.terrain)
        start, delta, length = _segment_geometry(
            x11_0, x12_0, altitude_0, x11_1, x12_1, altitude_1)
        fractions = _segment_fractions(start, delta, length, self.terrain)
        speed = None
        if time_0 is not None and time_1 is not None and time_1 > time_0:
            speed = (altitude_1 - altitude_0) / (time_1 - time_0)
        for share in fractions:
            x11, x12, altitude = _point_on_segment(start, delta, share)
            time = (None if time_0 is None
                    else time_0 + share * (time_1 - time_0))
            self.observe(x11, x12, altitude, time=time, vertical_speed=speed)
        return collision

    def summary(self):
        """Вернуть сводку для отчёта или подписи кадра."""
        return {
            'samples': self.samples,
            'min_clearance': self.min_clearance,
            'min_point': self.min_point,
            'events': list(self.events),
        }


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
