#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Внешний адаптер звука тренажёра «Глиссада-6» (этап 12 плана).

Модуль работает только на хосте. Он принимает события игры в том виде,
в каком их пишут регистратор ``GLRECF.FTN`` и модель отказов ``GLFAULT.FTN``,
строит по явной таблице описания звуковых сигналов и записывает их в файл
формата ``WAV`` стандартными средствами Python. Никаких внешних библиотек
и обращений к звуковым устройствам нет: результат — обычный звуковой файл.

Принцип К-71: пульты и индикация рабочих мест, а также звуковые и двигательные
сигналы — периферия. Ядро модели в ``SRC/`` этот модуль не трогает.

Запуск демонстрационного прогона:

    python3 TOOLS/sound_adapter.py demo
    python3 TOOLS/sound_adapter.py демо --out /tmp/мой-прогон.wav
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
import wave
from pathlib import Path

# ---------------------------------------------------------------------------
# Блок настроек адаптера. Как и блоки /SCPAR/, /RECPAR/, /FAULT/ в ядре,
# все настройки вынесены сюда и не разбросаны по телу модуля.
# ---------------------------------------------------------------------------

SOUND_PARAMS = {
    'sample_rate': 8000,     # частота дискретизации, отсчётов в секунду
    'sample_width': 2,       # байт на один отсчёт (знаковое целое)
    'gap_s': 0.05,           # пауза между соседними сигналами, секунды
    'attack_s': 0.01,        # нарастание огибающей в начале сигнала
    'release_s': 0.03,       # затухание огибающей в конце сигнала
}

# Явная таблица «событие — частота, длительность, амплитуда».
# Частота задана в герцах, длительность — в секундах,
# амплитуда — в долях от полной шкалы отсчёта.
EVENT_CUES = {
    'TOUCHDOWN': {
        'label': 'посадка', 'freq_hz': 330.0, 'duration_s': 0.55,
        'amplitude': 0.55, 'waveform': 'sine',
    },
    'STALL': {
        'label': 'сваливание', 'freq_hz': 180.0, 'duration_s': 0.70,
        'amplitude': 0.70, 'waveform': 'square',
    },
    'FAULT': {
        'label': 'отказ', 'freq_hz': 660.0, 'duration_s': 0.40,
        'amplitude': 0.60, 'waveform': 'square',
    },
    'GLIDE': {
        'label': 'вход в глиссаду', 'freq_hz': 880.0, 'duration_s': 0.25,
        'amplitude': 0.40, 'waveform': 'sine',
    },
    'WARNING': {
        'label': 'предупреждение', 'freq_hz': 520.0, 'duration_s': 0.35,
        'amplitude': 0.50, 'waveform': 'square',
    },
}

# Коды отказов из ``SRC/GLFAULT.FTN``: 1 — потеря тяги,
# 2 — заклинивание руля высоты, 3 — заклинивание элеронов,
# 4 — заклинивание руля направления, 5 — сдвиг ветра.
# В потоке телеметрии они приходят строками вида ``EV 1 K=1 T= ...``.
FAULT_LABELS = {
    1: 'потеря тяги',
    2: 'заклинивание руля высоты',
    3: 'заклинивание элеронов',
    4: 'заклинивание руля направления',
    5: 'сдвиг ветра',
}

# Подписи форм сигнала для журнала и командной строки.
WAVEFORM_LABELS = {
    'sine': 'синус',
    'square': 'прямоугольник',
}

# События демонстрационного прогона в порядке появления.
DEMO_EVENTS = ['GLIDE', 'WARNING', 'STALL', 'FAULT', 'TOUCHDOWN']

DEFAULT_DEMO_PATH = Path('/tmp') / 'etap12-zvuk-demo.wav'


class SoundEventError(ValueError):
    """Ошибка в описании события: код не найден в явных таблицах."""


def normalize_event(raw: object) -> tuple[str, str | None]:
    """Привести событие к коду таблицы и необязательной русской подписи.

    Допустимы три вида записи: строка-код, целый код отказа из ``GLFAULT``
    и объект с полем ``event`` (либо ``kind``, либо ``code``).
    """
    if isinstance(raw, bool):
        raise SoundEventError('логическое значение не является событием')
    if isinstance(raw, int):
        if raw in FAULT_LABELS:
            return 'FAULT', FAULT_LABELS[raw]
        raise SoundEventError('неизвестный код отказа: ' + str(raw))
    if isinstance(raw, str):
        name = raw.strip().upper()
        if name in EVENT_CUES:
            return name, None
        if name.isdigit() and int(name) in FAULT_LABELS:
            code = int(name)
            return 'FAULT', FAULT_LABELS[code]
        raise SoundEventError('неизвестное событие: ' + repr(raw))
    if isinstance(raw, dict):
        code = raw.get('code')
        if isinstance(code, int) and not isinstance(code, bool) and code in FAULT_LABELS:
            return 'FAULT', str(raw.get('label') or FAULT_LABELS[code])
        name = raw.get('event', raw.get('kind', raw.get('name')))
        if not isinstance(name, str):
            raise SoundEventError('в объекте события нет поля event')
        event, label = normalize_event(name)
        override = raw.get('label')
        if isinstance(override, str) and override.strip():
            return event, override.strip()
        return event, label
    raise SoundEventError('неподдерживаемый вид события: ' + repr(raw))


class SoundAdapter:
    """Преобразование событий игры в описания сигналов и файл формата WAV."""

    def __init__(self, params: dict | None = None, table: dict | None = None):
        self.params = dict(SOUND_PARAMS)
        if params is not None:
            self.params.update(params)
        self.table = dict(EVENT_CUES if table is None else table)
        if self.params['sample_rate'] <= 0:
            raise SoundEventError('частота дискретизации должна быть положительной')
        if self.params['sample_width'] != 2:
            raise SoundEventError('поддерживается только два байта на отсчёт')

    def cues(self, events) -> list[dict]:
        """Вернуть список описаний сигналов в порядке событий.

        Каждое описание содержит код события, русскую подпись, частоту,
        длительность, амплитуду, форму и момент начала в секундах.
        """
        result: list[dict] = []
        clock = 0.0
        for raw in events:
            name, custom_label = normalize_event(raw)
            spec = self.table[name]
            cue = {
                'event': name,
                'label': custom_label or spec['label'],
                'freq_hz': float(spec['freq_hz']),
                'duration_s': float(spec['duration_s']),
                'amplitude': float(spec['amplitude']),
                'waveform': spec['waveform'],
                'start_s': round(clock, 6),
            }
            if cue['waveform'] not in WAVEFORM_LABELS:
                raise SoundEventError('неизвестная форма сигнала: '
                                      + str(cue['waveform']))
            if cue['freq_hz'] <= 0 or cue['duration_s'] <= 0:
                raise SoundEventError('частота и длительность должны быть положительными')
            if not 0.0 < cue['amplitude'] <= 1.0:
                raise SoundEventError('амплитуда должна быть в пределах от нуля до единицы')
            result.append(cue)
            clock += cue['duration_s'] + self.params['gap_s']
        return result

    def _frames(self, cue: dict) -> list[int]:
        """Сформировать отсчёты одного сигнала с огибающей."""
        rate = self.params['sample_rate']
        count = int(round(cue['duration_s'] * rate))
        attack = max(1, int(round(self.params['attack_s'] * rate)))
        release = max(1, int(round(self.params['release_s'] * rate)))
        if count < attack + release:
            attack = release = max(1, count // 2)
        phase = 2.0 * math.pi * cue['freq_hz'] / rate
        peak = 32767.0 * cue['amplitude']
        samples: list[int] = []
        for index in range(count):
            value = math.sin(phase * index)
            if cue['waveform'] == 'square':
                value = 1.0 if value >= 0.0 else -1.0
            if index < attack:
                envelope = (index + 1) / (attack + 1)
            elif index >= count - release:
                envelope = (count - index) / (release + 1)
            else:
                envelope = 1.0
            level = int(round(peak * envelope * value))
            samples.append(max(-32768, min(32767, level)))
        return samples

    def write_wav(self, cues: list[dict], path) -> str:
        """Записать описанные сигналы в файл формата WAV и вернуть путь."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        rate = self.params['sample_rate']
        frames: list[int] = []
        gap_frames = int(round(self.params['gap_s'] * rate))
        for index, cue in enumerate(cues):
            frames.extend(self._frames(cue))
            if index < len(cues) - 1:
                frames.extend([0] * gap_frames)
        with wave.open(str(target), 'wb') as handle:
            handle.setnchannels(1)
            handle.setsampwidth(self.params['sample_width'])
            handle.setframerate(rate)
            handle.setnframes(len(frames))
            if frames:
                handle.writeframes(struct.pack('<%dh' % len(frames), *frames))
        return str(target)

    def describe(self, cues: list[dict]) -> list[str]:
        """Вернуть строки журнала с русскими подписями сигналов."""
        lines = []
        for number, cue in enumerate(cues, 1):
            lines.append(
                'СИГНАЛ {}: {} | частота={:.0f} Гц | длительность={:.2f} с | '
                'амплитуда={:.2f} | форма={} | начало={:.2f} с'.format(
                    number, cue['label'], cue['freq_hz'], cue['duration_s'],
                    cue['amplitude'], WAVEFORM_LABELS[cue['waveform']],
                    cue['start_s']))
        return lines


def run_demo(out=None, log=print) -> str:
    """Прогнать демонстрационный набор событий и записать звуковой файл."""
    adapter = SoundAdapter()
    cues = adapter.cues(DEMO_EVENTS)
    target = Path(out) if out is not None else DEFAULT_DEMO_PATH
    written = adapter.write_wav(cues, target)
    log('ДЕМОНСТРАЦИЯ ЗВУКА: сигналов {}'.format(len(cues)))
    for line in adapter.describe(cues):
        log(line)
    log('ФАЙЛ: ' + written)
    return written


def load_events(path) -> list[object]:
    """Прочитать события из файла: список в формате JSON или строки JSONL."""
    import json
    text = Path(path).read_text(encoding='utf-8')
    stripped = text.strip()
    if stripped.startswith('['):
        return json.loads(stripped)
    return [json.loads(line) for line in stripped.splitlines() if line.strip()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    demo = sub.add_parser('demo', aliases=['демо'],
                          help='создать демонстрационный звуковой файл')
    demo.add_argument('--out', metavar='ФАЙЛ',
                      help='куда записать файл формата WAV')
    demo.add_argument('--events', metavar='ФАЙЛ',
                      help='взять события из файла вместо демонстрационных')
    args = parser.parse_args(argv)
    if args.events:
        events = load_events(args.events)
        adapter = SoundAdapter()
        cues = adapter.cues(events)
        target = Path(args.out) if args.out else DEFAULT_DEMO_PATH
        written = adapter.write_wav(cues, target)
        print('СИГНАЛОВ ПО СОБЫТИЯМ: {}'.format(len(cues)))
        for line in adapter.describe(cues):
            print(line)
        print('ФАЙЛ: ' + written)
        return 0
    try:
        run_demo(args.out)
    except (SoundEventError, OSError) as exc:
        print('ОШИБКА: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
