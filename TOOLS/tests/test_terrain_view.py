#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты хостового показа поля рельефа ``TOOLS/terrain_view.py``."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))

import terrain as tr  # noqa: E402
import terrain_view as tv  # noqa: E402

# Фрагмент настоящего потока RPL: научная запись без разделителей.
SAMPLE = [
    'FRAMES=2 EVENTS=1 NSTEP=50',
    'TELE   1 T= 5.00E+00',
    '  X= 7.6490E+01-4.7850E+00 0.0000E+00 9.99918E-01 0.00000E+00',
    '      0.00000E+00-1.28326E-02 0.00000E+00 0.00000E+00 5.83645E-04',
    '       -1.46E+04  0.000E+00  7.662E+02',
    '  U= 5.50307E-02 0.00000E+00 0.00000E+00 3.88435E-01',
    'TELE   2 T= 1.00E+01',
    '  X= 7.5252E+01-4.6853E+00 0.0000E+00 9.99980E-01 0.00000E+00',
    '      0.00000E+00 6.32334E-03 0.00000E+00 0.00000E+00 2.69897E-02',
    '       -1.42E+04  0.000E+00  7.451E+02',
    '  U= 5.58682E-02 0.00000E+00 0.00000E+00 4.20006E-01',
    'EV     1 K=1 T= 0.00E+00',
]


class ParseTelemetryTests(unittest.TestCase):
    def test_single_frame_fields(self):
        frames = tv.parse_telemetry(SAMPLE[:6])
        self.assertEqual(len(frames), 1)
        frame = frames[0]
        self.assertEqual(frame['index'], 1)
        self.assertAlmostEqual(frame['time'], 5.0)
        self.assertAlmostEqual(frame['x11'], -14600.0)
        self.assertAlmostEqual(frame['x12'], 0.0)
        self.assertAlmostEqual(frame['alt'], 766.2)
        self.assertEqual(len(frame['x']), 13)
        self.assertEqual(len(frame['u']), 4)
        self.assertAlmostEqual(frame['x'][0], 76.490)

    def test_two_frames_and_events_ignored(self):
        frames = tv.parse_telemetry(SAMPLE)
        self.assertEqual([frame['index'] for frame in frames], [1, 2])
        self.assertAlmostEqual(frames[1]['time'], 10.0)
        self.assertAlmostEqual(frames[1]['x11'], -14200.0)

    def test_text_with_line_breaks_and_terminal_prefix(self):
        text = '\n'.join('> ' + line for line in SAMPLE[:6])
        frames = tv.parse_telemetry(text)
        self.assertEqual(len(frames), 1)
        self.assertAlmostEqual(frames[0]['alt'], 766.2)

    def test_empty_and_garbage_input(self):
        self.assertEqual(tv.parse_telemetry([]), [])
        self.assertEqual(tv.parse_telemetry(['ПУСТО', 'ЕЩЁ СТРОКА']), [])

    @unittest.skipUnless((TOOLS / 'replays' / 'tu104-cal.json').exists(),
                         'нет эталона tu104-cal.json')
    def test_real_reference_is_parsed(self):
        source = TOOLS / 'replays' / 'tu104-cal.json'
        spec = json.loads(source.read_text(encoding='utf-8'))
        frames = tv.parse_telemetry(spec['telemetry'])
        self.assertEqual(len(frames), spec['frames'])
        self.assertAlmostEqual(frames[-1]['alt'], 8.425, places=3)

    def test_load_frames_from_json_and_log(self):
        with tempfile.TemporaryDirectory() as folder:
            json_path = Path(folder) / 'sample.json'
            log_path = Path(folder) / 'sample.log'
            json_path.write_text(json.dumps({'telemetry': SAMPLE}),
                                 encoding='utf-8')
            log_path.write_text('\n'.join(SAMPLE), encoding='utf-8')
            self.assertEqual(len(tv.load_frames(json_path)), 2)
            self.assertEqual(len(tv.load_frames(log_path)), 2)
            self.assertEqual(len(tv.load_frames(SAMPLE)), 2)

    def test_load_frames_rejects_unknown_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'bad.json'
            path.write_text('{"other": 1}', encoding='utf-8')
            with self.assertRaises(ValueError):
                tv.load_frames(path)


class RenderFieldTests(unittest.TestCase):
    def setUp(self):
        self.frames = tv.parse_telemetry(SAMPLE)

    def test_render_contains_all_markers_and_captions(self):
        lines = tv.render_field(self.frames, width=50, height=10)
        text = '\n'.join(lines)
        for marker in ('#', '.', '*', '|'):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        for phrase in ('КАДР', 'ПРОСВЕТ СЕЙЧАС', 'МИНИМАЛЬНЫЙ',
                       'ПОРОГ ВПП', 'ГЛИССАДА', 'УСЛОВИЯ'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_render_shows_selected_frame(self):
        lines = tv.render_field(self.frames, width=50, frame_index=0)
        self.assertIn('КАДР   1', lines[0])
        lines = tv.render_field(self.frames, width=50, frame_index=1)
        self.assertIn('КАДР   2', lines[0])

    def test_render_uses_monitor_minimum(self):
        monitor = tr.ClearanceMonitor()
        monitor.observe(-14600.0, 0.0, -1000.0, time=5.0)
        lines = tv.render_field(self.frames, monitor=monitor,
                                width=50, height=10)
        text = '\n'.join(lines)
        self.assertIn('ЗАМЕРОВ = 1', text)
        self.assertIn('-1000.0', text)

    def test_render_rejects_bad_arguments(self):
        with self.assertRaises(ValueError):
            tv.render_field(self.frames, width=10)
        with self.assertRaises(ValueError):
            tv.render_field(self.frames, frame_index=-1)
        with self.assertRaises(ValueError):
            tv.render_field(self.frames, frame_index=99)

    def test_render_empty_frames(self):
        self.assertEqual(tv.render_field([]), ['НЕТ КАДРОВ ТЕЛЕМЕТРИИ'])

    def test_demo_frames_are_synthetic_but_valid(self):
        frames = tv.demo_frames()
        self.assertEqual(len(frames), len(tr.DEMO_STATES))
        self.assertTrue(all('x11' in frame and 'time' in frame
                            for frame in frames))


class CommandLineTests(unittest.TestCase):
    def test_demo_prints_frame(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = tv.main(['--demo', '--width', '40', '--height', '8'])
        self.assertEqual(code, 0)
        self.assertIn('КАДР', output.getvalue())
        self.assertIn('ПРОСВЕТ СЕЙЧАС', output.getvalue())

    def test_telemetry_option_reads_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sample.json'
            path.write_text(json.dumps({'telemetry': SAMPLE}),
                            encoding='utf-8')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = tv.main(['--telemetry', str(path),
                                '--width', '40', '--height', '8'])
        self.assertEqual(code, 0)
        self.assertIn('КАДР   2', output.getvalue())

    def test_bad_option_reports_error(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = tv.main(['--telemetry', '/нет/такого/файла.log'])
        self.assertEqual(code, 2)
        self.assertIn('ОШИБКА', errors.getvalue())

    def test_missing_source_is_rejected(self):
        with self.assertRaises(SystemExit):
            tv.main([])


if __name__ == '__main__':
    unittest.main()
