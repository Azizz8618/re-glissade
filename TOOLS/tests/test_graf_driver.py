#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты хост-драйвера графики на базе graf.pas."""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import graf_driver as gd  # noqa: E402


class EtalonTests(unittest.TestCase):
    """Побайтовая сверка с эталонными потоками mc-7401."""

    @classmethod
    def setUpClass(cls):
        cls.драйвер = gd.GrafDriver()

    def test_zag(self):
        проверка = self.драйвер.verify_etalon('ЗАГ')
        self.assertTrue(проверка['совпадает'], проверка)
        self.assertEqual(проверка['длина_потока'], 339)
        self.assertEqual(проверка['длина_эталона'], 339)

    def test_set(self):
        проверка = self.драйвер.verify_etalon('СЕТ')
        self.assertTrue(проверка['совпадает'], проверка)
        self.assertEqual(проверка['длина_потока'], 2994)

    def test_sol(self):
        проверка = self.драйвер.verify_etalon('СОЛ')
        self.assertTrue(проверка['совпадает'], проверка)
        self.assertEqual(проверка['длина_потока'], 1233)

    def test_unknown_scenario(self):
        with self.assertRaises(gd.НеизвестныйСценарий):
            self.драйвер.stream_from_scenario('НЕТ')
        with self.assertRaises(gd.НеизвестныйСценарий):
            self.драйвер.verify_etalon('НЕТ')


class RenderTests(unittest.TestCase):
    """Проверка сохранения кадра в формате PNG."""

    @classmethod
    def setUpClass(cls):
        cls.драйвер = gd.GrafDriver()
        cls.поток = cls.драйвер.stream_from_scenario('ЗАГ')

    def test_render_creates_png(self):
        with tempfile.TemporaryDirectory() as каталог:
            путь = self.драйвер.render(self.поток,
                                       Path(каталог) / 'кадр.png')
            self.assertTrue(путь.is_file())
            self.assertEqual(путь.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
            self.assertGreater(путь.stat().st_size, 100)

    def test_render_scenario_saves_stream_and_png(self):
        with tempfile.TemporaryDirectory() as каталог:
            драйвер = gd.GrafDriver(out_dir=каталог)
            путь = драйвер.render_scenario('ЗАГ', Path(каталог) / 'ЗАГ.png',
                                           scale=1)
            self.assertTrue(путь.is_file())
            self.assertEqual(
                (Path(каталог) / 'ЗАГ.bin').read_bytes(), self.поток
            )


class GameFrameTests(unittest.TestCase):
    """Отображение параметров кадра игры в приказы graf.pas."""

    @classmethod
    def setUpClass(cls):
        cls.драйвер = gd.GrafDriver()

    def test_explicit_command_with_numbers(self):
        план = self.драйвер.game_frame_plan(
            {'приказ': 'ГРА', 'числа': [5]}
        )
        self.assertEqual(план['приказ'], 'ГРА')
        self.assertEqual(план['числа'], [5])
        self.assertEqual(план['ввод'], 'ГРА 5 ВЫХ ')
        поток = self.драйвер.stream_from_game_frame(
            {'приказ': 'ГРА', 'числа': [5]}
        )
        self.assertIsInstance(поток, bytes)
        self.assertGreater(len(поток), 100)

    def test_game_fields_are_gap(self):
        params = {'T': 12.5, 'VERT': 3, 'скорость': 280}
        план = self.драйвер.game_frame_plan(params)
        self.assertEqual(план['приказ'], gd.СЦЕНАРИЙ_ПО_УМОЛЧАНИЮ)
        self.assertTrue(план['gap'])
        текст_gap = ' '.join(план['gap'])
        for поле in ('T', 'VERT', 'скорость'):
            self.assertIn(поле, текст_gap)
        self.assertEqual(
            self.драйвер.stream_from_game_frame(params),
            self.драйвер.stream_from_scenario('СЕТ'),
        )

    def test_unknown_game_command(self):
        with self.assertRaises(gd.НеизвестныйСценарий):
            self.драйвер.game_frame_plan({'приказ': 'НЕТ'})

    def test_numbers_for_wrong_command(self):
        with self.assertRaises(ValueError):
            self.драйвер.game_frame_plan({'приказ': 'СЕТ', 'числа': [3]})


class CommandLineTests(unittest.TestCase):
    """Проверка командной строки."""

    def test_list_and_verify(self):
        буфер = io.StringIO()
        with contextlib.redirect_stdout(буфер):
            код = gd.main(['list'])
        self.assertEqual(код, 0)
        self.assertIn('ЗАГ', буфер.getvalue())

        буфер = io.StringIO()
        with contextlib.redirect_stdout(буфер):
            код = gd.main(['verify', 'ЗАГ', 'СЕТ', 'СОЛ'])
        self.assertEqual(код, 0)
        self.assertEqual(буфер.getvalue().count('совпадает'), 3)

    def test_frame_from_json(self):
        with tempfile.TemporaryDirectory() as каталог:
            файл = Path(каталог) / 'params.json'
            файл.write_text(json.dumps({'приказ': 'ОКР', 'числа': [150]}),
                            encoding='utf-8')
            буфер = io.StringIO()
            with contextlib.redirect_stdout(буфер):
                код = gd.main(['frame', str(файл), '--out',
                               str(Path(каталог) / 'кадр.png')])
            self.assertEqual(код, 0)
            self.assertTrue((Path(каталог) / 'кадр.png').is_file())
            self.assertIn('ОКР', буфер.getvalue())

    def test_render_unknown_scenario_returns_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            код = gd.main(['render', 'НЕТ'])
        self.assertEqual(код, 2)


if __name__ == '__main__':
    unittest.main()
