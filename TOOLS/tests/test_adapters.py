#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты внешних адаптеров звука и платформы (этап 12)."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import platform_adapter as pa  # noqa: E402
import sound_adapter as sa  # noqa: E402


class SoundTableTests(unittest.TestCase):
    def test_expected_codes_are_present(self):
        for code in ('TOUCHDOWN', 'STALL', 'FAULT', 'GLIDE', 'WARNING'):
            self.assertIn(code, sa.EVENT_CUES)
            spec = sa.EVENT_CUES[code]
            self.assertGreater(spec['freq_hz'], 0)
            self.assertGreater(spec['duration_s'], 0)
            self.assertGreater(spec['amplitude'], 0)
            self.assertLessEqual(spec['amplitude'], 1)
            self.assertIn(spec['waveform'], sa.WAVEFORM_LABELS)

    def test_fault_codes_match_kernel(self):
        self.assertEqual(sorted(sa.FAULT_LABELS), [1, 2, 3, 4, 5])

    def test_cues_keep_order_and_timings(self):
        adapter = sa.SoundAdapter()
        cues = adapter.cues(['GLIDE', 'WARNING'])
        self.assertEqual([c['event'] for c in cues], ['GLIDE', 'WARNING'])
        self.assertEqual(cues[0]['start_s'], 0.0)
        expected = sa.EVENT_CUES['GLIDE']['duration_s'] + sa.SOUND_PARAMS['gap_s']
        self.assertAlmostEqual(cues[1]['start_s'], expected, places=5)
        self.assertEqual(cues[0]['label'], 'вход в глиссаду')
        self.assertEqual(cues[1]['waveform'], 'square')

    def test_telemetry_fault_code_becomes_cue(self):
        cues = sa.SoundAdapter().cues([{'code': 3, 't': 12.5}])
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0]['event'], 'FAULT')
        self.assertEqual(cues[0]['label'], 'заклинивание элеронов')

    def test_string_fault_code_becomes_cue(self):
        cues = sa.SoundAdapter().cues(['2'])
        self.assertEqual(cues[0]['label'], 'заклинивание руля высоты')

    def test_custom_label_is_kept(self):
        cues = sa.SoundAdapter().cues([{'event': 'TOUCHDOWN', 'label': 'посадочный удар'}])
        self.assertEqual(cues[0]['label'], 'посадочный удар')

    def test_unknown_events_are_rejected(self):
        adapter = sa.SoundAdapter()
        for raw in ('ПРИЗЕМЛЕНИЕ', 99, True, None, {}, {'event': 5.5}):
            with self.subTest(raw=raw), self.assertRaises(sa.SoundEventError):
                adapter.cues([raw])

    def test_empty_event_list(self):
        self.assertEqual(sa.SoundAdapter().cues([]), [])

    def test_log_uses_russian_labels(self):
        adapter = sa.SoundAdapter()
        lines = adapter.describe(adapter.cues(['TOUCHDOWN']))
        self.assertEqual(len(lines), 1)
        self.assertIn('посадка', lines[0])
        self.assertIn('синус', lines[0])
        self.assertIn('Гц', lines[0])


class SoundWavTests(unittest.TestCase):
    def test_header_and_duration(self):
        adapter = sa.SoundAdapter()
        cues = adapter.cues(['GLIDE', 'WARNING', 'FAULT'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'сигнал.wav'
            adapter.write_wav(cues, path)
            raw = path.read_bytes()
            self.assertEqual(raw[:4], b'RIFF')
            self.assertEqual(raw[8:12], b'WAVE')
            self.assertEqual(raw[12:16], b'fmt ')
            with wave.open(str(path), 'rb') as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getsampwidth(), 2)
                self.assertEqual(handle.getframerate(), sa.SOUND_PARAMS['sample_rate'])
                frames = handle.getnframes()
                samples = handle.readframes(frames)
        expected = (cues[-1]['start_s'] + cues[-1]['duration_s'])
        self.assertAlmostEqual(frames / sa.SOUND_PARAMS['sample_rate'],
                              expected, delta=0.002)
        self.assertEqual(len(samples), frames * 2)

    def test_samples_are_inside_amplitude(self):
        adapter = sa.SoundAdapter()
        cue = adapter.cues(['STALL'])[0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'сигнал.wav'
            adapter.write_wav([cue], path)
            with wave.open(str(path), 'rb') as handle:
                frames = handle.readframes(handle.getnframes())
        import struct
        values = struct.unpack('<%dh' % (len(frames) // 2), frames)
        limit = int(32767 * cue['amplitude']) + 1
        self.assertLessEqual(max(abs(v) for v in values), limit)
        self.assertGreater(max(abs(v) for v in values), limit // 2)

    def test_envelope_starts_and_ends_quietly(self):
        adapter = sa.SoundAdapter()
        samples = adapter._frames(adapter.cues(['TOUCHDOWN'])[0])
        self.assertEqual(abs(samples[0]) < 5000, True)
        self.assertEqual(abs(samples[-1]) < 5000, True)

    def test_empty_cues_give_valid_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'пусто.wav'
            sa.SoundAdapter().write_wav([], path)
            raw = path.read_bytes()
            self.assertEqual(raw[:4], b'RIFF')
            self.assertEqual(raw[8:12], b'WAVE')
            with wave.open(str(path), 'rb') as handle:
                self.assertEqual(handle.getnframes(), 0)


class PlatformTests(unittest.TestCase):
    def test_all_three_axes_present(self):
        state = {'vert': 1.0, 'speed': 70.0, 'g_load': 1.5,
                 'controls': {'pitch': 0.2, 'roll': -0.2}}
        commands = pa.PlatformAdapter().commands(state)
        self.assertEqual([c['axis'] for c in commands], ['pitch', 'roll', 'heave'])
        self.assertEqual([c['unit'] for c in commands],
                         ['градус', 'градус', 'метр'])

    def test_limits_are_never_exceeded(self):
        state = {'vert': 1000.0, 'speed': 5000.0, 'g_load': 100.0,
                 'controls': {'pitch': 10.0, 'roll': -10.0}}
        for command in pa.PlatformAdapter().commands(state):
            self.assertLessEqual(abs(command['value']), command['limit'])
        self.assertEqual(pa.clamp(50.0, 8.0), 8.0)
        self.assertEqual(pa.clamp(-50.0, 8.0), -8.0)

    def test_neutral_state_gives_zero(self):
        state = {'vert': 0.0, 'speed': pa.REFERENCE_SPEED, 'g_load': pa.REFERENCE_G,
                 'controls': {'pitch': 0.0, 'roll': 0.0}}
        values = [c['value'] for c in pa.PlatformAdapter().commands(state)]
        self.assertEqual(values, [0.0, 0.0, 0.0])

    def test_direction_of_response(self):
        base = {'vert': 0.0, 'speed': pa.REFERENCE_SPEED, 'g_load': 1.0,
                'controls': {'pitch': 0.0, 'roll': 0.0}}
        adapter = pa.PlatformAdapter()
        plus_g = dict(base, g_load=1.5)
        plus_roll = dict(base, controls={'pitch': 0.0, 'roll': 0.5})
        plus_vert = dict(base, vert=1.0)
        self.assertGreater(adapter.commands(plus_g)[0]['value'], 0)
        self.assertGreater(adapter.commands(plus_roll)[1]['value'], 0)
        self.assertGreater(adapter.commands(plus_vert)[2]['value'], 0)

    def test_controls_accept_list_from_recorder(self):
        state = {'vert': 0.0, 'speed': 70.0, 'g_load': 1.0,
                 'controls': [0.5, -0.5, 0.0, 1.0]}
        values = [c['value'] for c in pa.PlatformAdapter().commands(state)]
        self.assertGreater(values[0], 0)
        self.assertLess(values[1], 0)

    def test_bad_states_rejected(self):
        good = {'vert': 0.0, 'speed': 70.0, 'g_load': 1.0,
                'controls': {'pitch': 0.0, 'roll': 0.0}}
        cases = [
            [],
            {'vert': 0.0},
            dict(good, vert='ноль'),
            dict(good, g_load=float('inf')),
            dict(good, controls={}),
            dict(good, controls=[0.1]),
        ]
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(pa.StateFormatError):
                pa.PlatformAdapter().commands(raw)

    def test_write_json(self):
        state = {'vert': 0.5, 'speed': 70.0, 'g_load': 1.1,
                 'controls': {'pitch': 0.1, 'roll': 0.0}}
        commands = pa.PlatformAdapter().commands(state)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'команды.json'
            written = pa.PlatformAdapter().write_json(commands, path)
            data = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(written, str(path))
        self.assertEqual(len(data), 3)
        self.assertEqual([item['label'] for item in data],
                         ['тангаж', 'крен', 'вертикальное перемещение'])


class DemoTests(unittest.TestCase):
    def test_sound_demo_creates_file_and_prints_signals(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'демо.wav'
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = sa.main(['demo', '--out', str(path)])
            self.assertEqual(code, 0)
            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes()[:4], b'RIFF')
        text = out.getvalue()
        self.assertIn('ДЕМОНСТРАЦИЯ ЗВУКА', text)
        self.assertIn('посадка', text)
        self.assertIn('сваливание', text)

    def test_platform_demo_creates_file_and_prints_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'демо.json'
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = pa.main(['демо', '--out', str(path)])
            self.assertEqual(code, 0)
            data = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(len(data), len(pa.DEMO_STATES) * 3)
        self.assertTrue(all(0 <= item['frame'] <= len(pa.DEMO_STATES) for item in data))
        self.assertIn('КАДР 1', out.getvalue())
        self.assertIn('ФАЙЛ:', out.getvalue())

    def test_aliases_work(self):
        with tempfile.TemporaryDirectory() as directory:
            sound = Path(directory) / 'з.wav'
            platform = Path(directory) / 'п.json'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sa.main(['демо', '--out', str(sound)]), 0)
                self.assertEqual(pa.main(['demo', '--out', str(platform)]), 0)
            self.assertTrue(sound.exists())
            self.assertTrue(platform.exists())


if __name__ == '__main__':
    unittest.main()
