#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты минимального моста СМ-2 ↔ Э-60 (кадры DKS D6/D7)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sm2_dks_bridge as bridge  # noqa: E402


class FrameFormatTests(unittest.TestCase):
    def test_ping_request_bytes(self):
        req = bridge.encode_frame(bridge.OP_PING, chan=2)
        self.assertEqual(req.hex(" "), "d6 04 02 00 00 00 00 00")
        self.assertEqual(len(req), bridge.FRAME_LEN)

    def test_write_request_bytes(self):
        # 0154 — системный запрос Э-60; 0400 — слово «звонок».
        req = bridge.encode_frame(bridge.OP_WRITE, chan=2,
                                  addr=bridge.CELL_REQUEST, val=0o400)
        self.assertEqual(req.hex(" "), "d6 02 02 00 6c 01 00 00")

    def test_read_request_bytes(self):
        req = bridge.encode_frame(bridge.OP_READ, chan=2, addr=0o50000)
        self.assertEqual(req.hex(" "), "d6 01 02 50 00 00 00 00")

    def test_response_decode(self):
        reply = bridge.decode_response(bytes.fromhex("d7 84 02 00 00 00 00 00"))
        self.assertEqual(reply.op, bridge.OP_PING)
        self.assertEqual(reply.name, "PING")
        self.assertEqual(reply.chan, 2)

    def test_response_without_reply_bit_rejected(self):
        with self.assertRaises(bridge.DksProtocolError):
            bridge.decode_response(bytes.fromhex("d6 04 02 00 00 00 00 00"))

    def test_response_with_bad_magic_rejected(self):
        with self.assertRaises(bridge.DksProtocolError):
            bridge.decode_response(bytes.fromhex("d5 84 02 00 00 00 00 00"))

    def test_short_response_rejected(self):
        with self.assertRaises(bridge.DksProtocolError):
            bridge.decode_response(bytes.fromhex("d7 84 02"))

    def test_invalid_fields_rejected(self):
        with self.assertRaises(bridge.DksProtocolError):
            bridge.encode_frame(bridge.OP_PING, chan=7)
        with self.assertRaises(bridge.DksProtocolError):
            bridge.encode_frame(bridge.OP_PING, addr=0o200000)


class Sm2WordsTests(unittest.TestCase):
    def test_frame_words_roundtrip(self):
        frame = bridge.DksFrame(bridge.OP_WRITE, chan=2,
                                addr=bridge.CELL_REQUEST, val=0o400)
        words = bridge.Sm2KAdapter.frame_to_words(frame)
        self.assertEqual(words, [0o153002, 0o001000, 0o066001, 0])
        restored = bridge.Sm2KAdapter.words_to_frame(words)
        self.assertEqual(restored.to_request(), frame.to_request())
        self.assertEqual(restored.addr, bridge.CELL_REQUEST)
        self.assertEqual(restored.val, 0o400)

    def test_deposit_and_ini_commands(self):
        frame = bridge.DksFrame(bridge.OP_PING, chan=2)
        words = bridge.Sm2KAdapter.frame_to_words(frame)
        deposits = bridge.Sm2KAdapter.deposit_commands(words, base=0o100)
        self.assertEqual(deposits[0], "DEPOSIT 000100 153004")
        self.assertIn("DEPOSIT SM2KD 153004",
                      bridge.Sm2KAdapter.sm2k_commands(words[0]))
        self.assertIn("DEPOSIT SM2KF 1",
                      bridge.Sm2KAdapter.sm2k_commands(words[0]))
        ini = bridge.Sm2KAdapter.build_ini(frame, sc=0o20)
        self.assertIn("SET CPU SM2", ini)
        self.assertIn("SET SM2K SC=020", ini)
        self.assertIn("QUIT", ini)
        self.assertNotIn("RUN", ini)  # каркас загрузки, не задача RCV/SND


class LoopbackTests(unittest.TestCase):
    def test_ping_write_read_handshake(self):
        """Живой TCP-обмен с хостовым эмулятором протокола."""
        messages = []
        server = bridge.LoopbackDksServer(
            log=lambda text: messages.append("эмулятор: " + text))
        port = server.start()
        try:
            with bridge.DksLink("127.0.0.1", port,
                                log=messages.append) as link:
                reply = link.ping()
                self.assertEqual(reply.op, bridge.OP_PING)

                link.write(bridge.CELL_REQUEST, 0o400)
                value = link.read(bridge.CELL_REQUEST)
                self.assertEqual(value, 0o400)
        finally:
            server.stop()

        joined = "\n".join(messages)
        self.assertIn("ОТПРАВЛЕНО", joined)
        self.assertIn("ПОЛУЧЕНО", joined)
        self.assertIn("PING", joined)
        self.assertIn("WRITE", joined)
        self.assertEqual(server.counters["PING"], 1)
        self.assertEqual(server.counters["WRITE"], 1)
        self.assertEqual(server.counters["READ"], 1)
        self.assertEqual(server.counters["BAD"], 0)

    def test_mismatched_op_rejected(self):
        """Если сервер ответил чужим опкодом, клиент обязан заметить."""
        messages = []
        server = bridge.LoopbackDksServer(log=lambda text: None)
        port = server.start()
        try:
            with bridge.DksLink("127.0.0.1", port, log=messages.append) as link:
                link.ping()
                # Прямо испортим следующий ответ сервера: подменим эмулятор
                # крошечным сокетом, который вернёт PING вместо WRITE.
                import socket
                rogue = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                rogue.connect(("127.0.0.1", port))
                req = bridge.encode_frame(bridge.OP_WRITE, addr=bridge.CELL_REQUEST,
                                          val=0o400)
                rogue.sendall(req)
                bridge.read_exact(rogue, bridge.FRAME_LEN)
                rogue.sendall(bytes([0xD7, 0x84, 2, 0, 0, 0, 0, 0]))
                with self.assertRaises(bridge.DksProtocolError):
                    bridge.decode_response(bridge.read_exact(rogue,
                                                             bridge.FRAME_LEN))
                rogue.close()
        finally:
            server.stop()


@unittest.skipUnless(os.environ.get("SM2_DKS_LIVE") == "1",
                     "живой мост включается переменной SM2_DKS_LIVE=1")
class LiveBridgeTests(unittest.TestCase):
    def test_live_ping(self):
        host = os.environ.get("SM2_DKS_HOST", "127.0.0.1")
        port = int(os.environ.get("SM2_DKS_PORT", "4140"))
        with bridge.DksLink(host, port) as link:
            reply = link.ping()
        self.assertEqual(reply.op, bridge.OP_PING)


if __name__ == "__main__":
    unittest.main(verbosity=2)
