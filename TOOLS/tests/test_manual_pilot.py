"""Тесты закона ручного пилота упражнения T2."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import exercises as ex  # noqa: E402


FRAME = b'''T= 6.0E+01 TIP=1 DALN= 1.0E+04 VYS= 5.2E+02 Y= 1.0E+00
 SKOR= 7.5E+01 VERT=-4.00E+00 ATAKA= 5.0E+00 TYAG= 5.0E+01
'''


def test_parse_frame():
    f = ex.parse_frame(FRAME.decode('utf-8'))
    assert f is not None
    assert f['daln'] == 10000.0
    assert f['vys'] == 520.0
    assert f['vert'] == -4.0


def test_parse_frame_incomplete():
    assert ex.parse_frame('T= 6.0E+01 TIP=1 DALN= 1.0E+04 VYS= 5.2E+02') is None


def test_decision_trims_to_goal():
    state = {'de': 0.0, 'dtz': 0.6}
    frame = {'daln': 10000.0, 'vys': 524.0, 'skor': 72.0, 'vert': -4.2}
    cmds = ex.manual_decision(frame, state)
    assert all(c in ('EV+', 'EV-', 'TH+', 'TH-') for c in cmds)
    assert abs(state['de']) <= ex.MANUAL['de_max']
    assert 0.0 <= state['dtz'] <= ex.MANUAL['dtz_max']


def test_decision_flare():
    state = {'de': 0.0, 'dtz': 0.6}
    frame = {'daln': 400.0, 'vys': 20.0, 'skor': 73.0, 'vert': -4.0}
    ex.manual_decision(frame, state)
    assert state['de'] >= ex.MANUAL['flare_de'] - 0.02


def test_decision_is_deterministic():
    f = {'daln': 10000.0, 'vys': 524.0, 'skor': 72.0, 'vert': -4.2}
    a, b = {'de': 0.0, 'dtz': 0.6}, {'de': 0.0, 'dtz': 0.6}
    assert ex.manual_decision(f, a) == ex.manual_decision(f, b)
