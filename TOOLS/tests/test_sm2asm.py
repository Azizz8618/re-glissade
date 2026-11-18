#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты минимального ассемблера СМ-2 (sm2asm.py)."""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sm2asm  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TASKS = os.path.join(REPO_ROOT, "TOOLS", "sm2_tasks")
PS1 = os.path.join(TASKS, "ps1.asm")
SIMH = "/home/azizz/Yandex.Disk/simh/BIN/hp2100"


class AssemblerTests(unittest.TestCase):
    def test_ps1_words(self):
        with open(PS1, "r", encoding="utf-8") as handle:
            words, labels, start = sm2asm.assemble(handle.read())
        mapping = dict(words)
        self.assertEqual(start, 0)
        self.assertEqual(labels["NUM"], 0o10)
        self.assertEqual(labels["PERIOD"], 0o11)
        self.assertEqual(labels["OUT"], 0o12)
        self.assertEqual(mapping[0], 0o0060010)  # LDA NUM
        self.assertEqual(mapping[1], 0o0040011)  # ADA PERIOD
        self.assertEqual(mapping[2], 0o0070012)  # STA OUT
        self.assertEqual(mapping[3], 0o0102000)  # HLT
        self.assertEqual(mapping[0o10], 5)
        self.assertEqual(mapping[0o11], 7)
        self.assertEqual(mapping[0o12], 0)

    def test_unknown_mnemonic_reports_line(self):
        source = "        .ORG 0\nSTART:  FOOBAR 1\n"
        with self.assertRaises(sm2asm.AssemblerError) as ctx:
            sm2asm.assemble(source)
        self.assertEqual(ctx.exception.line_no, 2)
        self.assertIn("FOOBAR", ctx.exception.message)

    def test_labels_and_expressions(self):
        source = (
            "        .ORG 0\n"
            "START:  LDA DATA+1\n"
            "        HLT\n"
            "DATA:   .WORD 10, 0d20, 0x10\n"
        )
        words, labels, start = sm2asm.assemble(source)
        mapping = dict(words)
        self.assertEqual(start, 0)
        self.assertEqual(mapping[0], 0o0060003)
        self.assertEqual(mapping[2], 0o10)   # 10 восьмеричное = 8
        self.assertEqual(mapping[3], 20)      # 0d20 — десятичное 20
        self.assertEqual(mapping[4], 0o20)    # 0x10 — шестнадцатеричное 10

    def test_extended_opcodes(self):
        source = (
            "        .ORG 0\n"
            "        DLD PTR\n"
            "        MPY 3\n"
            "        ASR\n"
            "        HLT\n"
            "PTR:    .WORD 0\n"
        )
        words, labels, _ = sm2asm.assemble(source)
        self.assertEqual([value for _, value in words[:5]],
                         [0o001100, labels["PTR"], 0o000100, 3, 0o000011])
        self.assertEqual(words[5][1], 0o0102000)

    def test_ini_and_dump(self):
        with open(PS1, "r", encoding="utf-8") as handle:
            words, labels, start = sm2asm.assemble(handle.read())
        with tempfile.TemporaryDirectory() as tmp:
            ini = os.path.join(tmp, "ps1.ini")
            dump = os.path.join(tmp, "ps1.map")
            sm2asm.write_ini(ini, words, start, labels["OUT"], "ps1.asm")
            sm2asm.write_dump(dump, words, "ps1.asm")
            with open(ini, "r", encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("SET CPU SM2", text)
            self.assertIn("DEPOSIT 000000 060010", text)
            self.assertIn("DEPOSIT P 00000", text)
            self.assertIn("RUN", text)
            self.assertIn("EXAMINE 000012", text)
            self.assertTrue(text.rstrip().endswith("QUIT"))
            with open(dump, "r", encoding="utf-8") as handle:
                self.assertIn("000000    060010", handle.read())

    @unittest.skipUnless(os.path.exists(SIMH), "симулятор hp2100 не собран")
    def test_ps1_in_simulator(self):
        """Прогнать PS1 в эмуляторе и сверить результат NUM + PERIOD."""
        with open(PS1, "r", encoding="utf-8") as handle:
            words, labels, start = sm2asm.assemble(handle.read())
        with tempfile.TemporaryDirectory() as tmp:
            ini = os.path.join(tmp, "ps1.ini")
            sm2asm.write_ini(ini, words, start, labels["OUT"], "ps1.asm")
            with open(ini, "rb") as script:
                result = subprocess.run(
                    [SIMH], stdin=script, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, timeout=30, check=False,
                )
            output = result.stdout.decode("utf-8", errors="replace")
            self.assertIn("12:", output, output)
            self.assertIn("000014", output, output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
