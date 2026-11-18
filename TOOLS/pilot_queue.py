#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Доставка команд пульта пилота и инструктора в реальном времени.

Модуль закрывает этап Q6 плана ``docs/PLAN-PERIFERIYA.md``. Он читает
заранее подготовленную очередь событий (одна строка — один объект
с полями ``step`` и ``cmd``), следит за границами шагов модели и в нужный
момент пересылает код команды в ячейку системного запроса Э-60 через
уже существующий мост ``sm2_dks_bridge.py``.

Принцип важен: хост только транспортирует код команды. Настоящая обработка
команд внутри прошивки СВЯЗЬ7 / ``GLDIAL.PAS`` не восстановлена — это
честно описано в ``docs/analysis/pilot-realtime.md``.

Запуск:

    python3 TOOLS/pilot_queue.py --events events.jsonl --dry-run
    python3 TOOLS/pilot_queue.py --events events.jsonl --host 127.0.0.1 --port 4140
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
BRIDGE = HERE / 'sm2_dks_bridge.py'


# ---------------------------------------------------------------------------
# Таблица кодов команд
# ---------------------------------------------------------------------------
# Числа 1..8   — ручное управление пилота (совпадает с MANUAL в GLDIAL.PAS),
# числа 16..23 — остальные команды пилота,
# числа 32..42 — команды инструктора (режим PIL в GLDIAL.PAS).
# Диапазоны 9..15 и 24..31 оставлены свободными для будущих команд.
# Код пишется в младший байт 16-разрядного слова; старший байт равен нулю.

COMMAND_CODES: Dict[str, int] = {
    # ручное управление
    'EV+': 1,   # прибавить отклонение руля высоты
    'EV-': 2,   # убавить отклонение руля высоты
    'AI+': 3,   # прибавить отклонение элеронов
    'AI-': 4,   # убавить отклонение элеронов
    'RU+': 5,   # прибавить отклонение руля направления
    'RU-': 6,   # убавить отклонение руля направления
    'TH+': 7,   # прибавить тягу
    'TH-': 8,   # убавить тягу
    # режим пилота
    'STA': 16,  # запустить моделирование
    'STE': 17,  # сделать один шаг
    'STO': 18,  # остановить моделирование
    'PAR': 19,  # запрос параметров и перезапуск
    'PRN': 20,  # напечатать форму
    'AUTO': 21,  # включить автопилот
    'INS': 22,  # перейти в режим инструктора
    'EXIT': 23,  # выйти
    # режим инструктора
    'SEL': 32,  # выбрать упражнение
    'FRZ': 33,  # заморозить модель
    'UNF': 34,  # снять заморозку
    'INJ': 35,  # ввести отказ
    'EPS': 36,  # задать порог ошибки
    'REC': 37,  # включить запись
    'RPL': 38,  # воспроизвести запись
    'RST': 39,  # очистить запись
    'SCR': 40,  # вывести снимок
    'HLP': 41,  # справка
    'PIL': 42,  # вернуться в режим пилота
}

COMMAND_DESCRIPTIONS: Dict[str, str] = {
    'EV+': 'руль высоты: прибавить отклонение',
    'EV-': 'руль высоты: убавить отклонение',
    'AI+': 'элероны: прибавить отклонение',
    'AI-': 'элероны: убавить отклонение',
    'RU+': 'руль направления: прибавить отклонение',
    'RU-': 'руль направления: убавить отклонение',
    'TH+': 'тяга: прибавить',
    'TH-': 'тяга: убавить',
    'STA': 'запуск моделирования',
    'STE': 'один шаг моделирования',
    'STO': 'останов моделирования',
    'PAR': 'параметры и перезапуск',
    'PRN': 'печать формы',
    'AUTO': 'включение автопилота',
    'INS': 'переход в режим инструктора',
    'EXIT': 'выход из тренажёра',
    'SEL': 'выбор упражнения',
    'FRZ': 'заморозка модели',
    'UNF': 'снятие заморозки',
    'INJ': 'ввод отказа',
    'EPS': 'задание порога ошибки',
    'REC': 'включение записи',
    'RPL': 'воспроизведение записи',
    'RST': 'очистка записи',
    'SCR': 'вывод снимка',
    'HLP': 'справка',
    'PIL': 'возврат в режим пилота',
}

CODE_NAMES: Dict[int, str] = {code: name for name, code in COMMAND_CODES.items()}

# Ячейка системного запроса Э-60. Совпадает с константой CELL_REQUEST
# модуля sm2_dks_bridge.py; записью этой ячейки команда уходит кадром WRITE.
DEFAULT_ADDR = 0o154


class EventFormatError(ValueError):
    """Ошибка в описании события: неверная запись файла или поле."""


class UnknownCommandError(EventFormatError):
    """Команды нет в явной таблице кодов."""


def encode_command(cmd: str) -> int:
    """Вернуть 16-разрядный код команды из явной таблицы.

    Имена команд приводятся к верхнему регистру и очищаются от пробелов,
    поэтому в файле событий допустимы ``ev+`` и ``  STA  ``.
    """
    if not isinstance(cmd, str):
        raise UnknownCommandError('команда должна быть строкой, получено '
                                  + repr(cmd))
    name = cmd.strip().upper()
    if name not in COMMAND_CODES:
        raise UnknownCommandError('неизвестная команда ' + repr(cmd))
    code = COMMAND_CODES[name]
    if not 0 <= code <= 0xFFFF:
        raise UnknownCommandError('код команды ' + name + ' не помещается в слово')
    return code


def decode_command(code: int) -> str:
    """Вернуть имя команды по коду (для журналов и проверок)."""
    if code not in CODE_NAMES:
        raise UnknownCommandError('неизвестный код команды ' + str(code))
    return CODE_NAMES[code]


@dataclass(frozen=True)
class Event:
    """Одно событие очереди: номер границы шага и команда."""

    step: int
    cmd: str

    def __post_init__(self) -> None:
        """Привести имя к верхнему регистру и сразу проверить код."""
        if not isinstance(self.cmd, str):
            raise UnknownCommandError('команда должна быть строкой')
        object.__setattr__(self, 'cmd', self.cmd.strip().upper())
        encode_command(self.cmd)

    @property
    def code(self) -> int:
        return encode_command(self.cmd)

    def describe(self) -> str:
        return 'шаг={:<4} команда={:<4} код={:06o}'.format(
            self.step, self.cmd, self.code)


def parse_event(raw: object, lineno: int = 0) -> Event:
    """Проверить одну запись файла событий и собрать событие."""
    where = 'строка {}'.format(lineno) if lineno else 'запись'
    if not isinstance(raw, dict):
        raise EventFormatError(where + ': ожидался объект с полями step и cmd')
    if 'step' not in raw or 'cmd' not in raw:
        raise EventFormatError(where + ': нужны поля step и cmd')
    step = raw['step']
    if isinstance(step, bool) or not isinstance(step, int):
        raise EventFormatError(where + ': step должен быть целым числом')
    if step < 1:
        raise EventFormatError(where + ': step начинается с единицы')
    cmd = raw['cmd']
    if not isinstance(cmd, str):
        raise EventFormatError(where + ': cmd должна быть строкой')
    try:
        return Event(step=step, cmd=cmd.strip().upper())
    except UnknownCommandError as exc:
        raise EventFormatError(where + ': ' + str(exc)) from exc


class PilotEventQueue:
    """Очередь команд с доставкой на границах шагов модели.

    Событие считается доступным на своём шаге и на всех последующих: если
    цикл пропустил границу, команда не теряется и уйдёт при первом же вызове
    ``due`` с номером не меньше шага события. Повторно команда не выдаётся.
    """

    def __init__(self, events: Optional[List[Event]] = None,
                 log: Optional[Callable[[str], None]] = None):
        self._pending: List[Event] = []
        self._delivered: List[Event] = []
        self._all: List[Event] = []
        self._log = log or (lambda text: print(text))
        for event in events or []:
            self.add(event.step, event.cmd)

    @classmethod
    def from_file(cls, path, log: Optional[Callable[[str], None]] = None
                  ) -> 'PilotEventQueue':
        """Прочитать файл событий: одна строка — один объект."""
        queue = cls(log=log)
        source = Path(path)
        with source.open('r', encoding='utf-8') as handle:
            for lineno, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise EventFormatError('{}: строка {}: неверный объект: {}'
                                           .format(source, lineno, exc)) from exc
                queue.add_event(parse_event(raw, lineno))
        return queue

    def set_log(self, log: Callable[[str], None]) -> None:
        """Заменить приёмник сообщений журнала."""
        self._log = log

    def add(self, step: int, cmd: str) -> Event:
        """Добавить событие в очередь, сохраняя порядок внутри шага."""
        return self.add_event(parse_event({'step': step, 'cmd': cmd}))

    def add_event(self, event: Event) -> Event:
        """Вставить уже проверенное событие по месту в упорядоченной очереди."""
        if not isinstance(event, Event):
            raise EventFormatError('ожидалось событие')
        index = 0
        while index < len(self._pending) and self._pending[index].step <= event.step:
            index += 1
        self._pending.insert(index, event)
        self._all.append(event)
        return event

    def plan(self) -> Tuple[Event, ...]:
        """Вернуть все события в порядке шагов (для пробного прогона)."""
        return tuple(sorted(self._all, key=lambda item: item.step))

    @property
    def pending(self) -> Tuple[Event, ...]:
        """Ещё не доставленные события."""
        return tuple(self._pending)

    @property
    def delivered(self) -> Tuple[Event, ...]:
        """Уже доставленные события."""
        return tuple(self._delivered)

    def due(self, step: int) -> List[str]:
        """Отдать команды, срок которых наступил к шагу ``step``.

        Возвращаются только имена команд; события помечаются доставленными
        и больше не выдаются. Пустой список означает, что на этом шаге
        передавать нечего.
        """
        if isinstance(step, bool) or not isinstance(step, int) or step < 1:
            raise EventFormatError('номер шага должен быть целым числом от единицы')
        names: List[str] = []
        while self._pending and self._pending[0].step <= step:
            event = self._pending.pop(0)
            self._delivered.append(event)
            names.append(event.cmd)
        return names

    def deliver(self, link, step: int, addr: Optional[int] = None
                ) -> List[Tuple[str, int]]:
        """Отправить все доступные на шаге команды через мост ДКС.

        ``link`` — объект с методом ``write(addr, val)`` (например, ``DksLink``
        из моста ``sm2_dks_bridge.py``). Возвращаются пары «команда, код».
        """
        target = DEFAULT_ADDR if addr is None else addr
        if not 0 <= target <= 0xFFFF:
            raise EventFormatError('адрес ячейки вне 16-разрядного диапазона')
        sent: List[Tuple[str, int]] = []
        for cmd in self.due(step):
            code = encode_command(cmd)
            link.write(target, code)
            self._log('ОТПРАВЛЕНО: шаг={} команда={} код={:06o} адрес={:06o}'
                      .format(step, cmd, code, target))
            sent.append((cmd, code))
        return sent

    def reset(self) -> None:
        """Вернуть все события в состояние «не доставлено»."""
        self._pending = sorted(self._all, key=lambda item: item.step)
        self._delivered = []


_BRIDGE_CACHE = None


def load_bridge():
    """Загрузить мост ДКС по пути файла, как это делает ``timeline.py``."""
    global _BRIDGE_CACHE
    if _BRIDGE_CACHE is None:
        spec = importlib.util.spec_from_file_location('sm2_dks_bridge', BRIDGE)
        module = importlib.util.module_from_spec(spec)
        sys.modules['sm2_dks_bridge'] = module
        spec.loader.exec_module(module)
        _BRIDGE_CACHE = module
    return _BRIDGE_CACHE


def print_table() -> None:
    """Напечатать явную таблицу кодов команд и их назначение."""
    print('Код (восьм.) | Команда | Назначение')
    for name, code in COMMAND_CODES.items():
        print('       {:04o} | {:<6} | {}'.format(
            code, name, COMMAND_DESCRIPTIONS[name]))


def _octal(text: str) -> int:
    """Разобрать восьмеричный адрес из командной строки."""
    try:
        value = int(text, 8)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('нужен восьмеричный адрес') from exc
    if not 0 <= value <= 0xFFFF:
        raise argparse.ArgumentTypeError('адрес вне 16-разрядного диапазона')
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', metavar='FILE',
                        help='файл событий: одна строка — один объект')
    parser.add_argument('--dry-run', action='store_true',
                        help='показать план доставки без сети')
    parser.add_argument('--host', default='127.0.0.1',
                        help='адрес сервера моста ДКС')
    parser.add_argument('--port', type=int, default=4140,
                        help='порт сервера моста ДКС')
    parser.add_argument('--addr', type=_octal, default=DEFAULT_ADDR,
                        help='ячейка запроса Э-60, восьмеричное (по умолчанию 154)')
    parser.add_argument('--tick', type=float, default=0.1,
                        help='пауза между шагами в секундах в живом режиме')
    parser.add_argument('--log', metavar='FILE',
                        help='записать сообщения о доставке в файл')
    parser.add_argument('--table', action='store_true',
                        help='напечатать таблицу кодов и выйти')
    args = parser.parse_args(argv)

    if args.table:
        print_table()
        return 0
    if not args.events:
        parser.error('нужен ключ --events (или --table)')
    if args.tick < 0:
        parser.error('пауза между шагами не может быть отрицательной')

    log_file = None

    def emit(text):
        print(text)
        if log_file is not None:
            log_file.write(text + '\n')
            log_file.flush()

    try:
        if args.log:
            log_file = open(args.log, 'w', encoding='utf-8')
        queue = PilotEventQueue.from_file(args.events, log=emit)
        plan = queue.plan()
        last_step = max((event.step for event in plan), default=0)
        if args.dry_run:
            emit('ПРОБНЫЙ ПРОГОН: событий {}'.format(len(plan)))
            for step in range(1, last_step + 1):
                for cmd in queue.due(step):
                    code = encode_command(cmd)
                    emit('ДОСТАВКА: шаг={} команда={} код={:06o} адрес={:06o}'
                         .format(step, cmd, code, args.addr))
            emit('ПРОБНЫЙ ПРОГОН: сеть не использовалась')
            return 0

        bridge = load_bridge()
        try:
            link = bridge.DksLink(host=args.host, port=args.port,
                                  log=emit).connect()
        except (bridge.DksTimeout, bridge.DksProtocolError, OSError) as exc:
            emit('ОШИБКА: мост ДКС недоступен: ' + str(exc))
            return 1
        try:
            for step in range(1, last_step + 1):
                queue.deliver(link, step, addr=args.addr)
                if step < last_step and args.tick > 0:
                    time.sleep(args.tick)
        finally:
            link.close()
        emit('ДОСТАВЛЕНО: {} команд'.format(len(queue.delivered)))
        return 0
    except (EventFormatError, OSError) as exc:
        emit('ОШИБКА: ' + str(exc))
        return 2
    finally:
        if log_file is not None:
            log_file.close()


if __name__ == '__main__':
    sys.exit(main())
