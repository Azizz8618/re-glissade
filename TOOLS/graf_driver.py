#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Хост-драйвер графики варианта C на базе эталонной программы graf.pas.

Программа ``mc-7401/golden/graf.pas`` исполняется на хосте транслятором
пакета ``pascal``. На вход ей подаётся текст приказов оператора терминала,
на выходе получается поток команд в линию. Этот поток отдаётся эмулятору
``mc7401``, который и рисует кадр.

Модуль не изменяет файлы проекта ``mc-7401``: он только читает их и
импортирует. Снятые потоки и нарисованные кадры пишутся в каталог ``TOOLS/graf``.

Примеры вызова из командной строки::

    python3 TOOLS/graf_driver.py verify
    python3 TOOLS/graf_driver.py render ЗАГ
    python3 TOOLS/graf_driver.py frame params.json
    python3 TOOLS/graf_driver.py list
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Корень этого репозитория и каталог для сгенерированных потоков и кадров.
КОРЕНЬ = Path(__file__).resolve().parent.parent
КАТАЛОГ_ВЫВОДА = КОРЕНЬ / 'TOOLS' / 'graf'

# Имена приказов терминала и тексты, которые оператор вводил бы с клавиатуры.
# Взято из mc-7401/tools/gen_golden.py и из таблицы приказов graf.pas.
СЦЕНАРИИ = {
    'СЕТ': ('СЕТ ', 'сетка: рамка и линии через семь точек'),
    'СОЛ': ('СОЛ ', 'солнце: сто пятьдесят концентрических окружностей'),
    'КОТ': ('КОТ ', 'кот: криволинейный рисунок'),
    'ЦЕП': ('ЦЕП ', 'цепь: имитация схемы'),
    'ФУН': ('ФУН ', 'функция: затухающая синусоида с рамкой'),
    'ЗАГ': ('ЗАГ ', 'заголовок: титульный экран с текстом'),
    'СИМ': ('СИМ ', 'символы: таблица знаков и заказные знаки'),
    'ТЕК': ('ТЕК ПРИВЕТ МС 7401' + chr(255) + ' ', 'текст: вывод строки символов'),
    'ЛИН': ('ЛИН 3 ', 'линии: образцы типов линий от одного до семи'),
    'ОКР': ('ОКР 150 ', 'окружности: серия окружностей со смещением окна'),
    'ГРА': ('ГРА 12 ', 'граф: полный граф на двенадцати вершинах'),
    'ШАР': ('ШАР ', 'шар: псевдообъёмный шар'),
    'ЛЕД': ('ЛЕД ', 'леди: фигура «леди»'),
    'УЗО': ('УЗО ', 'узор: фрактальный узор'),
    'РОЗ': ('РОЗ ', 'роза: розетка со случайным именем'),
    'ТИП': ('ТИП 3 СЕТ ', 'тип линии три и сетка'),
    'ЧАС': ('ЧАС 12 30 1 150 ', 'часы: циферблат со стрелками'),
    'ПТИ': ('ПТИ 5 120 ', 'птица: анимация полёта, начальный кадр'),
    'КИНО': ('КИН 15 120 ', 'кино: движение окружности'),
}

# Приказы, после которых graf.pas читает десятичные числа подпрограммой
# ТАКЕ/СТАКЕ. Количество чисел указано по тексту graf.pas.
ПРИКАЗЫ_С_ЧИСЛАМИ = {
    'ГРА': 1, 'ОКР': 1, 'ЛИН': 1, 'ТИП': 1,
    'ЧАС': 3, 'КИН': 2, 'КИНО': 2, 'ПТИ': 2,
}

# Приказ, который завершает работу graf.pas. Пробел после него обязателен:
# подпрограмма ПРОБ пропускает пробелы при чтении ввода.
ПРИКАЗ_ВЫХОДА = 'ВЫХ '

# Поля кадра игры, перечисленные в плане диалога (раздел 6, пункт 1) и в
# задании на этот этап. У graf.pas нет ни одной входной переменной с такими
# именами, поэтому все они попадают в раздел GAP отчёта.
ПОЛЯ_ИГРЫ = (
    'T', 'DTM', 'X', 'VA', 'ALFA', 'U', 'THETA', 'GAM', 'PSI', 'EGLI',
    'VERT', 'отклонение', 'тип самолёта', 'скорость', 'время',
)

# Сценарий, который драйвер выбирает сам, если в параметрах кадра нет явного
# приказа. Это соглашение самого драйвера, а не свойство graf.pas.
СЦЕНАРИЙ_ПО_УМОЛЧАНИЮ = 'СЕТ'

# Псевдонимы ключей словаря параметров. Имена ключей допустимы латиницей
# как идентификаторы, но в отчёте используются только русские названия.
КЛЮЧИ_ПРИКАЗА = ('приказ', 'команда', 'сценарий')
КЛЮЧИ_ЧИСЕЛ = ('числа', 'аргументы', 'параметры')


class НеизвестныйСценарий(ValueError):
    """Запрошенный сценарий отсутствует в эталонной таблице."""


def найти_mc7401() -> Path:
    """Найти каталог внешнего проекта mc-7401 и проверить его состав."""
    указанный = os.environ.get('MC7401_ROOT')
    кандидаты = []
    if указанный:
        кандидаты.append(Path(указанный))
    кандидаты.extend((
        КОРЕНЬ.parent / 'mc-7401',
        Path('/home/azizz/Yandex.Disk/mc-7401'),
    ))
    for кандидат in кандидаты:
        if (кандидат / 'golden' / 'graf.pas').is_file():
            return кандидат.resolve()
    raise FileNotFoundError(
        'не найден каталог mc-7401 с файлом golden/graf.pas; '
        'укажите путь через переменную среды MC7401_ROOT'
    )


def ввод_сценария(name: str) -> str:
    """Вернуть текст, который вводится терминалу для заданного сценария."""
    if name not in СЦЕНАРИИ:
        raise НеизвестныйСценарий(
            f'неизвестный сценарий {name!r}; '
            f'доступны: {", ".join(СЦЕНАРИИ)}'
        )
    return СЦЕНАРИИ[name][0] + ПРИКАЗ_ВЫХОДА


class GrafDriver:
    """Драйвер: приказы терминала → поток байт → кадр в формате PNG."""

    def __init__(self, mc7401_root=None, out_dir=None):
        self.корень_mc = Path(mc7401_root).resolve() if mc7401_root \
            else найти_mc7401()
        self.каталог = Path(out_dir).resolve() if out_dir \
            else КАТАЛОГ_ВЫВОДА
        self._готов = False
        self._исходник = None
        self._паскаль = None
        self._рантайм = None
        self._mc7401 = None
        self._backend = None
        self._reader = None

    def _подготовить(self):
        """Однократно подключить внешний проект и перевести graf.pas."""
        if self._готов:
            return
        корень = str(self.корень_mc)
        tools = str(self.корень_mc / 'tools')
        for путь in (корень, tools):
            if путь not in sys.path:
                sys.path.insert(0, путь)

        import pascal                                      # noqa: E402
        import pascal.runtime as runtime                    # noqa: E402
        from mc7401 import TerminalEmulator                 # noqa: E402
        from mc7401.backends import PNGBackend              # noqa: E402
        from mc7401.reader import CommandStreamReader, EventKind  # noqa: E402

        self._паскаль = pascal
        self._рантайм = runtime
        self._mc7401 = TerminalEmulator
        self._backend = PNGBackend
        self._reader = (CommandStreamReader, EventKind)
        self._исходник = pascal.translate(
            str(self.корень_mc / 'golden' / 'graf.pas')
        )
        self._готов = True

    def _прогнать(self, текст: str) -> bytes:
        """Исполнить graf.pas с заданным вводом и вернуть поток в линию."""
        self._подготовить()
        try:
            return bytes(self._паскаль.run_source(self._исходник, текст)['wire'])
        except SystemExit:
            # graf.pas завершается командой выхода из программы, из-за чего
            # транслятор выбрасывает SystemExit. Поток остаётся в рантайме.
            return bytes(self._рантайм._terminal.wire)

    def stream_from_scenario(self, name: str) -> bytes:
        """Снять поток байт для эталонного сценария ``name``."""
        return self._прогнать(ввод_сценария(name))

    def verify_etalon(self, name: str) -> dict:
        """Сравнить снятый поток с эталонным файлом побайтово.

        Возвращается словарь с полями «имя», «длина_потока»,
        «длина_эталона», «совпадает» и «путь_эталона».
        """
        поток = self.stream_from_scenario(name)
        путь = self.корень_mc / 'golden' / 'streams' / f'{name}.bin'
        есть_файл = путь.is_file()
        эталон = путь.read_bytes() if есть_файл else b''
        return {
            'имя': name,
            'длина_потока': len(поток),
            'длина_эталона': len(эталон) if есть_файл else None,
            'совпадает': есть_файл and поток == эталон,
            'путь_эталона': str(путь),
        }

    def game_frame_plan(self, params: dict) -> dict:
        """Разложить параметры кадра игры на приказы graf.pas и GAP.

        Подтверждено только одно: graf.pas читает трёхлитерный приказ и,
        для некоторых приказов, десятичные числа. Поля модели полёта не имеют
        ввода в graf.pas и честно попадают в список неподтверждённого.
        """
        if not isinstance(params, dict):
            raise TypeError('параметры кадра должны быть словарём')

        приказ = None
        for ключ in КЛЮЧИ_ПРИКАЗА:
            значение_приказа = params.get(ключ)
            if значение_приказа:
                приказ = str(значение_приказа).strip().upper()
                break

        числа = []
        for ключ in КЛЮЧИ_ЧИСЕЛ:
            значение = params.get(ключ)
            if значение is None:
                continue
            список_чисел = значение if isinstance(значение, (list, tuple)) \
                else [значение]
            числа = [int(число) for число in список_чисел]
            break

        if числа and приказ not in ПРИКАЗЫ_С_ЧИСЛАМИ:
            raise ValueError(
                f'приказ {приказ} не принимает числа в graf.pas; '
                'числа допустимы только у ' +
                ', '.join(ПРИКАЗЫ_С_ЧИСЛАМИ)
            )

        gap = []
        подтверждено = 'приказ и числовые аргументы читаются graf.pas через ПРИКАЗ и ТАКЕ'

        if приказ is not None:
            известный_приказ = any(
                приказ == имя or приказ == текст.split()[0]
                for имя, (текст, _) in СЦЕНАРИИ.items()
            )
            if not известный_приказ:
                raise НеизвестныйСценарий(
                    f'graf.pas не знает приказ {приказ!r}; '
                    f'доступны: {", ".join(СЦЕНАРИИ)}'
                )
        else:
            приказ = СЦЕНАРИЙ_ПО_УМОЛЧАНИЮ
            gap.append(
                'явный приказ не задан: драйвер по своему соглашению берёт '
                f'{СЦЕНАРИЙ_ПО_УМОЛЧАНИЮ}; это не свойство graf.pas'
            )

        найденные_поля = [
            str(ключ) for ключ in params
            if any(str(ключ).upper() == str(поле).upper() for поле in ПОЛЯ_ИГРЫ)
        ]
        if найденные_поля:
            gap.append(
                'поля модели полёта ' + ', '.join(найденные_поля) +
                ' не имеют входа в graf.pas и не влияют на поток байт'
            )
        gap.append(
            'картинка «полоса ВПП, осевая пунктиром, глиссада три градуса, '
            'самолёт-крест, шкала отклонения» ни одним приказом graf.pas '
            'не рисуется; для неё нужна отдельная Pascal-программа'
        )

        части = [приказ] + [str(число) for число in числа]
        ввод = ' '.join(части) + ' ' + ПРИКАЗ_ВЫХОДА
        return {
            'приказ': приказ,
            'числа': числа,
            'ввод': ввод,
            'подтверждено': подтверждено,
            'gap': gap,
        }

    def stream_from_game_frame(self, params: dict) -> bytes:
        """Сформировать поток байт кадра игры по его параметрам."""
        план = self.game_frame_plan(params)
        return self._прогнать(план['ввод'])

    def pick_frame(self, wire: bytes):
        """Выбрать самое «наполненное» состояние экрана по потоку команд."""
        читатель_class, kind = self._reader
        emu = self._mc7401()
        best = emu.fb.copy()
        best_pts = 0
        reader = читатель_class()
        reader.feed(wire)
        reader.close()
        for ev in reader.pop():
            emu.handle_event(ev)
            if ev.kind is kind.COMMAND:
                точек = emu.fb.count_set()
                if точек > best_pts:
                    best, best_pts = emu.fb.copy(), точек
        if emu.fb.count_set() > best_pts:
            best = emu.fb
        return best, emu

    def render(self, wire: bytes, out_png, scale: int = 2) -> Path:
        """Сохранить кадр из потока ``wire`` в файл ``out_png``."""
        self._подготовить()
        кадр, _ = self.pick_frame(wire)
        путь = Path(out_png).resolve()
        путь.parent.mkdir(parents=True, exist_ok=True)
        self._backend(кадр, scale=scale).save(путь)
        return путь

    def save_stream(self, wire: bytes, имя: str) -> Path:
        """Записать поток байт в каталог вывода."""
        self.каталог.mkdir(parents=True, exist_ok=True)
        путь = self.каталог / f'{имя}.bin'
        путь.write_bytes(wire)
        return путь

    def render_scenario(self, name: str, out_png=None, scale: int = 2) -> Path:
        """Снять поток сценария и сразу сохранить кадр."""
        поток = self.stream_from_scenario(name)
        self.save_stream(поток, name)
        путь = out_png or (self.каталог / f'{name}.png')
        return self.render(поток, путь, scale=scale)

    def список_сценариев(self):
        """Вернуть пары «имя — описание» в порядке эталонной таблицы."""
        return [(имя, описание) for имя, (_, описание) in СЦЕНАРИИ.items()]


def main(argv=None) -> int:
    """Разбор аргументов командной строки."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('действие', choices=('verify', 'render', 'frame', 'list'),
                    help='verify — сверка, render — кадр сценария, '
                         'frame — кадр по файлу параметров, list — список')
    ap.add_argument('аргумент', nargs='?', help='имя сценария или путь к файлу')
    ap.add_argument('остальные', nargs='*', help='дополнительные имена для verify')
    ap.add_argument('--scale', type=int, default=2, help='масштаб изображения')
    ap.add_argument('--out', help='путь к выходному файлу')
    args = ap.parse_args(argv)

    драйвер = GrafDriver()
    if args.действие == 'list':
        for имя, описание in драйвер.список_сценариев():
            print(f'{имя}  {описание}')
        return 0

    if args.действие == 'verify':
        имена = ([args.аргумент] if args.аргумент else []) + args.остальные
        если_имена = имена or [имя for имя, _ in драйвер.список_сценариев()
                               if (драйвер.корень_mc / 'golden' / 'streams' /
                                   f'{имя}.bin').is_file()]
        плохо = 0
        for имя in если_имена:
            try:
                проверка = драйвер.verify_etalon(имя)
            except (НеизвестныйСценарий, FileNotFoundError) as exc:
                print(f'{имя}: ОШИБКА {exc}')
                плохо += 1
                continue
            метка = 'совпадает' if проверка['совпадает'] else 'НЕ СОВПАДАЕТ'
            print(f'{имя}: поток {проверка["длина_потока"]} байт, '
                  f'эталон {проверка["длина_эталона"]} байт — {метка}')
            if not проверка['совпадает']:
                плохо += 1
        return 1 if плохо else 0

    if args.действие == 'render':
        if not args.аргумент:
            print('ОШИБКА: укажите имя сценария', file=sys.stderr)
            return 2
        try:
            путь = драйвер.render_scenario(args.аргумент, args.out,
                                           scale=args.scale)
        except НеизвестныйСценарий as exc:
            print(f'ОШИБКА: {exc}', file=sys.stderr)
            return 2
        print(f'сценарий {args.аргумент}: кадр сохранён в {путь}')
        return 0

    if not args.аргумент:
        print('ОШИБКА: укажите путь к файлу параметров', file=sys.stderr)
        return 2
    try:
        params = json.loads(Path(args.аргумент).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        print(f'ОШИБКА: не удалось прочитать параметры: {exc}', file=sys.stderr)
        return 2
    try:
        план = драйвер.game_frame_plan(params)
        поток = драйвер.stream_from_game_frame(params)
    except (НеизвестныйСценарий, TypeError, ValueError) as exc:
        print(f'ОШИБКА: {exc}', file=sys.stderr)
        return 2
    драйвер.save_stream(поток, 'frame')
    путь = драйвер.render(поток, args.out or (драйвер.каталог / 'frame.png'),
                          scale=args.scale)
    print(f'приказ: {план["приказ"]}; ввод: {план["ввод"]!r}; '
          f'поток {len(поток)} байт; кадр {путь}')
    for запись in план['gap']:
        print(f'GAP: {запись}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
