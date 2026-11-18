#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты очереди доставки команд пульта пилота и инструктора."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pilot_queue as pq  # noqa: E402


class FakeLink:
    """Подставное соединение: запоминает записи вместо сети."""

    def __init__(self):
        self.calls = []

    def write(self, addr, val):
        self.calls.append((addr, val))


def write_events(directory, lines):
    path = Path(directory) / 'events.jsonl'
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


class CommandTableTests(unittest.TestCase):
    def test_all_commands_have_unique_codes(self):
        codes = list(pq.COMMAND_CODES.values())
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(0 <= code <= 0xFFFF for code in codes))

    def test_example_codes_match_specification(self):
        expected = {
            'EV+': 1, 'EV-': 2, 'AI+': 3, 'AI-': 4,
            'RU+': 5, 'RU-': 6, 'TH+': 7, 'TH-': 8,
            'STA': 16, 'STE': 17, 'STO': 18,
        }
        for name, code in expected.items():
            self.assertEqual(pq.encode_command(name), code)

    def test_instructor_codes_are_separate_range(self):
        for name in ('SEL', 'FRZ', 'UNF', 'INJ', 'EPS', 'REC',
                     'RPL', 'RST', 'SCR', 'HLP', 'PIL'):
            self.assertGreaterEqual(pq.encode_command(name), 32)
            self.assertLess(pq.encode_command(name), 64)

    def test_command_name_is_normalized(self):
        self.assertEqual(pq.encode_command('  ev+  '), 1)

    def test_unknown_command_rejected(self):
        with self.assertRaises(pq.UnknownCommandError):
            pq.encode_command('WRONG')
        with self.assertRaises(pq.UnknownCommandError):
            pq.encode_command(123)

    def test_decode_reverse(self):
        for name, code in pq.COMMAND_CODES.items():
            self.assertEqual(pq.decode_command(code), name)
        with self.assertRaises(pq.UnknownCommandError):
            pq.decode_command(999)


class LoadTests(unittest.TestCase):
    def test_load_jsonl_and_sort_by_step(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_events(directory, [
                json.dumps({'step': 5, 'cmd': 'TH+'}),
                '',
                json.dumps({'step': 1, 'cmd': 'EV+'}),
                json.dumps({'step': 3, 'cmd': 'STA'}),
                json.dumps({'step': 3, 'cmd': 'AI-'}),
            ])
            queue = pq.PilotEventQueue.from_file(path)
        plan = queue.plan()
        self.assertEqual([(e.step, e.cmd) for e in plan],
                         [(1, 'EV+'), (3, 'STA'), (3, 'AI-'), (5, 'TH+')])
        self.assertEqual([e.code for e in plan], [1, 16, 4, 7])

    def test_bad_records_rejected(self):
        cases = [
            ['not an object'],
            ['{"step": 1}'],
            ['{"cmd": "EV+"}'],
            ['{"step": 0, "cmd": "EV+"}'],
            ['{"step": 1.5, "cmd": "EV+"}'],
            ['{"step": true, "cmd": "EV+"}'],
            ['{"step": 1, "cmd": "WRONG"}'],
            ['{"step": 1, "cmd": 42}'],
        ]
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                path = write_events(directory, case)
                with self.assertRaises(pq.EventFormatError):
                    pq.PilotEventQueue.from_file(path)


class DueTests(unittest.TestCase):
    def setUp(self):
        self.queue = pq.PilotEventQueue()
        for step, cmd in ((1, 'EV+'), (2, 'AI-'), (4, 'STA'), (4, 'TH-')):
            self.queue.add(step, cmd)

    def test_due_on_boundaries(self):
        self.assertEqual(self.queue.due(1), ['EV+'])
        self.assertEqual(self.queue.due(1), [])
        self.assertEqual(self.queue.due(2), ['AI-'])
        self.assertEqual(self.queue.due(3), [])
        self.assertEqual(self.queue.due(4), ['STA', 'TH-'])
        self.assertEqual(self.queue.due(5), [])

    def test_skipped_boundary_does_not_lose_command(self):
        self.assertEqual(self.queue.due(3), ['EV+', 'AI-'])
        self.assertEqual(self.queue.due(3), [])

    def test_delivered_and_pending_are_separate(self):
        self.queue.due(2)
        self.assertEqual([e.cmd for e in self.queue.delivered], ['EV+', 'AI-'])
        self.assertEqual([e.step for e in self.queue.pending], [4, 4])

    def test_reset_returns_events_to_pending(self):
        self.queue.due(4)
        self.assertEqual(len(self.queue.delivered), 4)
        self.queue.reset()
        self.assertEqual(len(self.queue.pending), 4)
        self.assertEqual(self.queue.delivered, ())
        self.assertEqual(self.queue.due(1), ['EV+'])

    def test_bad_step_rejected(self):
        with self.assertRaises(pq.EventFormatError):
            self.queue.due(0)
        with self.assertRaises(pq.EventFormatError):
            self.queue.due(True)


class DeliverTests(unittest.TestCase):
    def setUp(self):
        self.messages = []
        self.queue = pq.PilotEventQueue(log=self.messages.append)
        self.queue.add(1, 'EV+')
        self.queue.add(2, 'STA')
        self.queue.add(2, 'PIL')

    def test_deliver_uses_default_cell_and_logs(self):
        link = FakeLink()
        sent = self.queue.deliver(link, 2)
        self.assertEqual(link.calls, [(0o154, 1), (0o154, 16), (0o154, 42)])
        self.assertEqual(sent, [('EV+', 1), ('STA', 16), ('PIL', 42)])
        self.assertEqual(len(self.messages), 3)
        self.assertTrue(all('ОТПРАВЛЕНО' in text for text in self.messages))
        self.assertIn('код=000020', self.messages[1])

    def test_deliver_does_not_repeat(self):
        link = FakeLink()
        self.queue.deliver(link, 2)
        self.assertEqual(self.queue.deliver(link, 2), [])
        self.assertEqual(self.queue.deliver(link, 9), [])
        self.assertEqual(len(link.calls), 3)

    def test_custom_address(self):
        link = FakeLink()
        self.queue.deliver(link, 1, addr=0o157)
        self.assertEqual(link.calls, [(0o157, 1)])

    def test_bad_address_rejected(self):
        with self.assertRaises(pq.EventFormatError):
            self.queue.deliver(FakeLink(), 1, addr=0o200000)

    def test_bridge_constants_match_default_cell(self):
        bridge = pq.load_bridge()
        self.assertEqual(bridge.CELL_REQUEST, pq.DEFAULT_ADDR)
        self.assertTrue(hasattr(bridge, 'DksLink'))


class CommandLineTests(unittest.TestCase):
    def test_table_option(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pq.main(['--table'])
        self.assertEqual(code, 0)
        self.assertIn('EV+', out.getvalue())
        self.assertIn('PIL', out.getvalue())

    def test_dry_run_shows_plan_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_events(directory, [
                json.dumps({'step': 2, 'cmd': 'EV+'}),
                json.dumps({'step': 1, 'cmd': 'STA'}),
            ])
            original = pq.load_bridge

            def forbidden():
                raise AssertionError('пробный прогон не должен трогать мост')

            pq.load_bridge = forbidden
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    code = pq.main(['--events', str(path), '--dry-run'])
            finally:
                pq.load_bridge = original
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn('шаг=1 команда=STA код=000020', text)
        self.assertIn('шаг=2 команда=EV+ код=000001', text)
        self.assertIn('сеть не использовалась', text)

    def test_missing_events_file_is_reported(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pq.main(['--events', '/нет/такого/файла.jsonl', '--dry-run'])
        self.assertEqual(code, 2)
        self.assertIn('ОШИБКА', out.getvalue())


if __name__ == '__main__':
    unittest.main()
