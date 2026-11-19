#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты хостового прототипа рельефа местности ``TOOLS/terrain.py``."""

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import terrain as tr  # noqa: E402


class TerrainProfileTests(unittest.TestCase):
    def setUp(self):
        # Явный профиль: тесты не зависят от чисел блока констант.
        self.profile = tr.TerrainProfile(
            longitudinal=[
                (-15000.0, 0.0), (-3000.0, 30.0),
                (0.0, 0.0), (2000.0, -5.0),
            ],
            lateral=[
                (-1000.0, 0.0), (-500.0, 50.0),
                (0.0, 0.0), (1000.0, 10.0),
            ],
            gear_height=2.5,
        )

    def test_interpolation_inside_longitudinal_segment(self):
        self.assertAlmostEqual(self.profile.elevation(-9000.0), 15.0)
        self.assertAlmostEqual(self.profile.elevation(-1500.0), 15.0)

    def test_interpolation_inside_lateral_segment(self):
        self.assertAlmostEqual(self.profile.elevation(-3000.0, -250.0), 55.0)
        self.assertAlmostEqual(self.profile.elevation(-3000.0, 500.0), 35.0)

    def test_combined_elevation(self):
        self.assertAlmostEqual(self.profile.elevation(-3000.0, -500.0), 80.0)

    def test_segment_boundaries_are_exact(self):
        for coord, height in ((-15000.0, 0.0), (-3000.0, 30.0),
                              (0.0, 0.0), (2000.0, -5.0)):
            with self.subTest(coord=coord):
                self.assertEqual(self.profile.elevation(coord, 0.0), height)

    def test_outside_profile_uses_edge_value(self):
        self.assertEqual(self.profile.elevation(-20000.0, 0.0), 0.0)
        self.assertEqual(self.profile.elevation(5000.0, 0.0), -5.0)
        self.assertEqual(self.profile.elevation(-3000.0, -2000.0), 30.0)
        self.assertEqual(self.profile.elevation(-3000.0, 5000.0), 40.0)

    def test_negative_coordinates(self):
        self.assertAlmostEqual(self.profile.elevation(-4500.0, -750.0), 51.25)

    def test_lateral_default_is_zero(self):
        self.assertEqual(self.profile.elevation(-3000.0),
                         self.profile.elevation(-3000.0, 0))

    def test_clearance_above_ground(self):
        self.assertAlmostEqual(self.profile.clearance(-3000.0, -500.0, 100.0), 20.0)

    def test_clearance_below_ground_is_negative(self):
        self.assertAlmostEqual(self.profile.clearance(-3000.0, -500.0, 75.0), -5.0)

    def test_touchdown_at_gear_height(self):
        self.assertTrue(self.profile.touchdown(-3000.0, -500.0, 82.5))

    def test_touchdown_below_and_above_gear_height(self):
        self.assertTrue(self.profile.touchdown(-3000.0, -500.0, 80.0))
        self.assertFalse(self.profile.touchdown(-3000.0, -500.0, 82.6))

    def test_profile_points_are_copy(self):
        rows = self.profile.profile_points()
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1], {'x11': -3000.0, 'elevation': 30.0})
        rows[0]['elevation'] = 999.0
        self.assertEqual(self.profile.elevation(-15000.0, 0.0), 0.0)

    def test_default_constructor_uses_constants(self):
        terrain = tr.TerrainProfile()
        self.assertEqual(terrain.gear_height, tr.GEAR_HEIGHT)
        self.assertEqual(terrain.elevation(0.0, 0.0), 0.0)
        self.assertEqual(len(terrain.profile_points()), len(tr.LONGITUDINAL_PROFILE))

    def test_flat_ground_reproduces_plain_touchdown(self):
        flat = tr.TerrainProfile(
            longitudinal=[(-15000.0, 0.0), (2500.0, 0.0)],
            lateral=[(-3000.0, 0.0), (3000.0, 0.0)],
            gear_height=1.8,
        )
        self.assertTrue(flat.touchdown(-100.0, 0.0, 1.8))
        self.assertFalse(flat.touchdown(-100.0, 0.0, 1.9))

    def test_invalid_profiles_are_rejected(self):
        bad = (
            [],
            [(0.0, 0.0), (0.0, 10.0)],
            [(0.0, 0.0), (-100.0, 10.0)],
            [(0.0, 0.0, 0.0)],
            [('ноль', 0.0), (100.0, 10.0)],
            [(0.0, float('nan'))],
        )
        for points in bad:
            with self.subTest(points=points), self.assertRaises(tr.TerrainFormatError):
                tr.TerrainProfile(longitudinal=points)

    def test_invalid_gear_height_is_rejected(self):
        with self.assertRaises(tr.TerrainFormatError):
            tr.TerrainProfile(gear_height=-1.0)

    def test_nonfinite_coordinate_is_rejected(self):
        with self.assertRaises(tr.TerrainFormatError):
            self.profile.elevation(float('nan'), 0.0)
        with self.assertRaises(tr.TerrainFormatError):
            self.profile.clearance(0.0, 0.0, float('inf'))


class DemoTests(unittest.TestCase):
    def test_demo_prints_russian_table_and_returns_zero(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = tr.main(['demo'])
        text = output.getvalue()
        self.assertEqual(code, 0)
        for phrase in ('ДЕМОНСТРАЦИЯ РЕЛЬЕФА МЕСТНОСТИ',
                       'ПРОДОЛЬНЫЙ ПРОФИЛЬ', 'ПОПЕРЕЧНЫЙ ПРОФИЛЬ',
                       'ПРИМЕРЫ РАСЧЁТА', 'ПРОСВЕТ', 'КАСАНИЕ',
                       'ПРОФИЛЬ УСЛОВНЫЙ'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn(str(int(tr.GEAR_HEIGHT)), text)

    def test_demo_alias_is_supported(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = tr.main(['демо'])
        self.assertEqual(code, 0)
        self.assertIn('ДЕМОНСТРАЦИЯ РЕЛЬЕФА МЕСТНОСТИ', output.getvalue())

    def test_demo_point_option(self):
        lines = []
        code = tr.run_demo(log=lines.append, point=(-1200.0, 0.0, 100.0))
        self.assertEqual(code, 0)
        sample = [line for line in lines if 'ПРОСВЕТ=' in line]
        self.assertEqual(len(sample), 1)
        self.assertIn('-1200.0', sample[0])
        self.assertIn('5.0', sample[0])
        self.assertIn('КАСАНИЕ=НЕТ', sample[0])

    def test_demo_rejects_bad_point(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = tr.main(['demo', '--point', 'nan', '0', '100'])
        self.assertEqual(code, 2)
        self.assertIn('ОШИБКА', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
