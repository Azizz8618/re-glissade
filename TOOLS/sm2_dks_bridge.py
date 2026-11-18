#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Минимальный мост СМ-2 ↔ «Электроника-60» для тренажёра «Глиссада-6».

Что делает этот модуль:

1. Кодирует и разбирает кадры моста DKS (D6/D7) в точном формате,
   описанном в docs/analysis/dks-bridge-runbook.md, раздел 5.1.
2. Держит TCP-соединение с сервером pdp11_dks.c (`SET DKS BRIDGE=port`)
   и выполняет запрос-ответ для PING, READ и WRITE.
3. Перекладывает кадр DKS в 16-разрядные слова СМ-2 и обратно,
   а также выдаёт готовые SIMH DEPOSIT-команды для регистра SM2KD
   и флага SM2KF контроллера «Сопряжение 2К».
4. Содержит честный хостовый эмулятор протокола (LoopbackDksServer),
   который проверяет формат кадра и квитирование без запуска simh.

ВАЖНО (GAP): этот модуль не меняет C-код simh. Прямой связи между
hp2100_sm2k.c и pdp11_dks.c внутри эмулятора не существует. Живая
связка «слово из SM2KD ушло кадром DKS в Э-60» остаётся открытым GAP;
здесь реализован транспортный уровень и генерация DEPOSIT-команд.

Запуск:

    python3 TOOLS/sm2_dks_bridge.py selftest
    python3 TOOLS/sm2_dks_bridge.py --loopback ping
    python3 TOOLS/sm2_dks_bridge.py --host 127.0.0.1 --port 4140 ping
    python3 TOOLS/sm2_dks_bridge.py --host 127.0.0.1 --port 4140 \
        write --addr 0154 --val 0400 --chan 2
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Константы протокола (по besm6_dks.c / pdp11_dks.h, см. ранебук, раздел 5)
# ---------------------------------------------------------------------------

MAGIC_REQUEST = 0xD6
MAGIC_RESPONSE = 0xD7
REPLY_BIT = 0x80          # те же 0200 восьмеричные в исходниках C
FRAME_LEN = 8
CHAN_MASK = 0x03
WORD_MASK = 0xFFFF        # 16-разрядное слово Э-60 / СМ-2

OP_READ = 0x01
OP_WRITE = 0x02
OP_ATTN = 0x03
OP_PING = 0x04
OP_BULK_READ = 0x05
OP_BULK_WRITE = 0x06

OP_NAMES = {
    OP_READ: "READ",
    OP_WRITE: "WRITE",
    OP_ATTN: "ATTN",
    OP_PING: "PING",
    OP_BULK_READ: "BULK_READ",
    OP_BULK_WRITE: "BULK_WRITE",
}

# Системные ячейки Э-60 (восьмеричные адреса)
CELL_KRK = 0o0
CELL_RING_S = 0o140
CELL_RING_H = 0o146
CELL_REQUEST = 0o154      # АБФОСS — системный запрос
CELL_REPLY = 0o157        # АБФОСH — системный ответ
CELL_DOORBELL = 0o177777  # адркс, «звонок»
CHANNEL_STATUS = 0o002000  # ячейка 0 при одном концентраторе на канале 2

SUPPORTED_OPS = (OP_READ, OP_WRITE, OP_ATTN, OP_PING)


class DksProtocolError(Exception):
    """Нарушение формата кадра DKS или неожиданный ответ."""


class DksTimeout(Exception):
    """Ответ от моста не пришёл за отведённое время."""


# ---------------------------------------------------------------------------
# Кадр
# ---------------------------------------------------------------------------

def encode_frame(op: int, chan: int = 2, addr: int = 0, val: int = 0,
                 payload: bytes = b"") -> bytes:
    """Собрать запросный кадр D6.

    Формат: D6 op chan addr_hi addr_lo val_hi val_lo 00 [payload].
    Все поля проверяются, чтобы не отправить в мост некорректный кадр.
    """
    if op not in OP_NAMES:
        raise DksProtocolError("неизвестный опкод DKS 0x{:02x}".format(op))
    if not 0 <= chan <= 3:
        raise DksProtocolError("номер канала КРК должен быть 0..3, получено "
                               + str(chan))
    if not 0 <= addr <= WORD_MASK:
        raise DksProtocolError("адрес {:o} вне 16-разрядного диапазона".format(addr))
    if not 0 <= val <= WORD_MASK:
        raise DksProtocolError("слово {:o} вне 16-разрядного диапазона".format(val))
    return bytes([
        MAGIC_REQUEST,
        op & 0xFF,
        chan & CHAN_MASK,
        (addr >> 8) & 0xFF,
        addr & 0xFF,
        (val >> 8) & 0xFF,
        val & 0xFF,
        0,
    ]) + bytes(payload)


def decode_response(data: bytes) -> "DksFrame":
    """Разобрать ответный кадр D7 и проверить его маркер и бит ответа."""
    if len(data) < FRAME_LEN:
        raise DksProtocolError(
            "короткий ответ: {} байт, нужно {}".format(len(data), FRAME_LEN))
    if data[0] != MAGIC_RESPONSE:
        raise DksProtocolError(
            "ожидался маркер D7, получен 0x{:02x}".format(data[0]))
    if not (data[1] & REPLY_BIT):
        raise DksProtocolError(
            "в ответе не выставлен бит 0200: op=0x{:02x}".format(data[1]))
    op = data[1] & ~REPLY_BIT
    if op not in OP_NAMES:
        raise DksProtocolError("неизвестный опкод в ответе 0x{:02x}".format(op))
    addr = (data[3] << 8) | data[4]
    val = (data[5] << 8) | data[6]
    return DksFrame(op=op, chan=data[2], addr=addr, val=val,
                    payload=bytes(data[FRAME_LEN:]), raw=bytes(data[:FRAME_LEN]))


@dataclass
class DksFrame:
    """Одно сообщение моста DKS."""

    op: int
    chan: int = 2
    addr: int = 0
    val: int = 0
    payload: bytes = b""
    raw: bytes = field(default=b"", repr=False)

    @property
    def name(self) -> str:
        return OP_NAMES.get(self.op, "OP?{:02x}".format(self.op))

    def to_request(self) -> bytes:
        return encode_frame(self.op, self.chan, self.addr, self.val, self.payload)

    def describe(self) -> str:
        return "D6 {} chan={} addr={:06o} val={:06o}".format(
            self.name, self.chan, self.addr, self.val)

    def describe_reply(self) -> str:
        return "D7 {} chan={} addr={:06o} val={:06o}".format(
            self.name, self.chan, self.addr, self.val)


def read_exact(sock: socket.socket, count: int) -> bytes:
    """Прочитать ровно count байт, ничего не потеряв в TCP-потоке."""
    chunks: List[bytes] = []
    left = count
    while left > 0:
        part = sock.recv(left)
        if not part:
            raise DksProtocolError(
                "соединение закрыто, получено {} из {} байт".format(
                    count - left, count))
        chunks.append(part)
        left -= len(part)
    return b"".join(chunks)


# ---------------------------------------------------------------------------
# Клиент моста (сторона, которая шлёт D6 — как БЭСМ-6 в эталонной связке)
# ---------------------------------------------------------------------------

class DksLink:
    """TCP-клиент кадра DKS с логированием «отправлено/получено»."""

    def __init__(self, host: str = "127.0.0.1", port: int = 4140,
                 timeout: float = 5.0,
                 log: Optional[Callable[[str], None]] = None,
                 stream=None):
        """
        stream — уже готовое соединение (используется встроенным эмулятором).
        log — callable, принимающий строку; по умолчанию print.
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self._log = log or (lambda text: print(text))
        self._sock: Optional[socket.socket] = stream

    def connect(self, retries: int = 1) -> "DksLink":
        if self._sock is not None:
            return self
        last_error = None
        for attempt in range(retries):
            try:
                self._sock = socket.create_connection(
                    (self.host, self.port), timeout=self.timeout)
                self._sock.settimeout(self.timeout)
                self._log("СОЕДИНЕНИЕ {}:{} установлено".format(
                    self.host, self.port))
                return self
            except OSError as exc:
                last_error = exc
        raise DksTimeout("не удалось подключиться к {}:{}: {}".format(
            self.host, self.port, last_error))

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self) -> "DksLink":
        return self.connect()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def transaction(self, frame: DksFrame) -> DksFrame:
        """Отправить кадр и получить квитирование D7."""
        if self._sock is None:
            raise DksProtocolError("нет соединения с мостом")
        request = frame.to_request()
        self._sock.sendall(request)
        self._log("ОТПРАВЛЕНО {:<48} [{}]".format(
            frame.describe(), request.hex(" ")))
        try:
            raw = read_exact(self._sock, FRAME_LEN)
        except socket.timeout as exc:
            raise DksTimeout("нет ответа на кадр {}".format(frame.name)) from exc
        reply = decode_response(raw)
        self._log("ПОЛУЧЕНО  {:<48} [{}]".format(
            reply.describe_reply(), raw.hex(" ")))
        if reply.op != frame.op:
            raise DksProtocolError(
                "в ответе опкод {}, ожидался {}".format(
                    reply.name, frame.name))
        return reply

    def ping(self, chan: int = 2) -> DksFrame:
        """Кадр 04 PING — проверка живости моста."""
        return self.transaction(DksFrame(op=OP_PING, chan=chan))

    def write(self, addr: int, val: int, chan: int = 2) -> DksFrame:
        """Кадр 02 WRITE — запись слова в ОЗУ Э-60.

        Поле val в ответе WRITE в эталонном тесте не проверяется, поэтому
        вызывающий должен пользоваться только фактом квитирования.
        """
        if addr == CELL_KRK or addr == CELL_DOORBELL:
            # Эти ячейки имеют побочные эффекты (выбор канала, звонок).
            self._log("ПРИМЕЧАНИЕ: адрес {:o} — системная ячейка с эффектом".format(addr))
        return self.transaction(
            DksFrame(op=OP_WRITE, chan=chan, addr=addr, val=val))

    def read(self, addr: int, chan: int = 2) -> int:
        """Кадр 01 READ — вернуть прочитанное 16-разрядное слово."""
        reply = self.transaction(DksFrame(op=OP_READ, chan=chan, addr=addr))
        return reply.val


# ---------------------------------------------------------------------------
# Честный хостовый эмулятор протокола (не подменяет pdp11_dks.c!)
# ---------------------------------------------------------------------------

class LoopbackDksServer:
    """Мини-эмулятор кадрового моста на хосте для самопроверки.

    Слушает TCP-порт, принимает одного клиента и отвечает на кадры
    PING / READ / WRITE / ATTN по тем же правилам, что и pdp11_dks.c.
    Это НЕ модель Э-60 и НЕ прошивка СВЯЗЬ7: только формат кадра
    и квитирование.
    """

    def __init__(self, port: int = 0, log=None):
        self.port = port
        self._log = log or (lambda text: None)
        self._listener: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.ram: Dict[int, int] = {CELL_KRK: CHANNEL_STATUS}
        self.counters: Dict[str, int] = {"PING": 0, "READ": 0,
                                         "WRITE": 0, "ATTN": 0, "BAD": 0}

    def start(self) -> int:
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind(("127.0.0.1", self.port))
        self._listener.listen(1)
        self._listener.settimeout(0.2)
        self.port = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self.port

    def stop(self) -> None:
        self._stop.set()
        if self._listener is not None:
            self._listener.close()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            conn.settimeout(1.0)
            try:
                while not self._stop.is_set():
                    try:
                        raw = read_exact(conn, FRAME_LEN)
                    except (socket.timeout, DksProtocolError):
                        break
                    reply = self._handle(raw)
                    conn.sendall(reply)
            finally:
                conn.close()
            if not self._stop.is_set():
                # Сервер моста принимает одного клиента; следующий вытесняет.
                continue

    def _handle(self, raw: bytes) -> bytes:
        if raw[0] != MAGIC_REQUEST or raw[7] != 0:
            self.counters["BAD"] += 1
            self._log("эмулятор: неверный кадр {}".format(raw.hex(" ")))
            return bytes([MAGIC_RESPONSE, REPLY_BIT | 0x7F]) + raw[2:]
        op = raw[1]
        chan = raw[2] & CHAN_MASK
        addr = (raw[3] << 8) | raw[4]
        val = (raw[5] << 8) | raw[6]
        name = OP_NAMES.get(op, "BAD")
        if name in self.counters:
            self.counters[name] += 1
        self._log("эмулятор: {} [{}]{:06o} {:06o}".format(
            name, chan, addr, val))
        if op == OP_PING:
            out_val = 0
        elif op == OP_ATTN:
            out_val = 0
        elif op == OP_READ:
            out_val = self.ram.get(addr, 0)
        elif op == OP_WRITE:
            self.ram[addr] = val
            out_val = val
        else:
            self.counters["BAD"] += 1
            out_val = 0
        return bytes([
            MAGIC_RESPONSE,
            op | REPLY_BIT,
            chan,
            (addr >> 8) & 0xFF,
            addr & 0xFF,
            (out_val >> 8) & 0xFF,
            out_val & 0xFF,
            0,
        ])


# ---------------------------------------------------------------------------
# Адаптер кадра DKS ↔ слова СМ-2 / SIMH DEPOSIT
# ---------------------------------------------------------------------------

class Sm2KAdapter:
    """Перекладывает кадр DKS в слова СМ-2 и команды SIMH.

    Регистр данных SM2KD — 16 бит, флаг готовности SM2KF — 1 бит;
    код выборки задаётся `SET SM2K SC=n`. Всё это объявлено в
    HP2100/hp2100_sm2k.c. Без правки C-кода хост может только
    сгенерировать DEPOSIT-команды и подать их в SIMH (например, через pty).
    """

    @staticmethod
    def frame_to_words(frame: DksFrame) -> List[int]:
        """8 байт кадра → четыре 16-разрядных слова СМ-2."""
        raw = frame.to_request()
        return [(raw[i] << 8) | raw[i + 1] for i in range(0, FRAME_LEN, 2)]

    @staticmethod
    def words_to_frame(words: List[int]) -> DksFrame:
        """Четыре слова СМ-2 → кадр DKS (обратное преобразование)."""
        if len(words) != FRAME_LEN // 2:
            raise DksProtocolError("нужно четыре слова, получено {}".format(len(words)))
        raw = bytearray()
        for word in words:
            if not 0 <= word <= WORD_MASK:
                raise DksProtocolError("слово {:o} не 16-разрядное".format(word))
            raw.append((word >> 8) & 0xFF)
            raw.append(word & 0xFF)
        if raw[0] != MAGIC_REQUEST or raw[7] != 0:
            raise DksProtocolError("слова не образуют кадр D6: {}".format(raw.hex(" ")))
        return DksFrame(op=raw[1], chan=raw[2] & CHAN_MASK,
                        addr=(raw[3] << 8) | raw[4],
                        val=(raw[5] << 8) | raw[6])

    @staticmethod
    def deposit_commands(words: List[int], base: int = 0o100) -> List[str]:
        """DEPOSIT-ы буфера кадра в память СМ-2 (адреса восьмеричные)."""
        return ["DEPOSIT {:06o} {:06o}".format(base + i, word)
                for i, word in enumerate(words)]

    @staticmethod
    def sm2k_commands(word: int) -> List[str]:
        """Выгрузка слова в SM2KD и поднятие флага SM2KF."""
        return [
            "DEPOSIT SM2KD {:06o}".format(word & WORD_MASK),
            "DEPOSIT SM2KF 1",
            "EXAMINE SM2KD",
        ]

    @classmethod
    def build_ini(cls, frame: DksFrame, base: int = 0o100,
                  sc: Optional[int] = None) -> str:
        """Собрать SIMH-скрипт загрузки кадра в СМ-2.

        Это каркас для загрузки, а не готовая задача RCV/SND: RUN намеренно
        не включается, пока задача на СМ-2 не собрана sm2asm.py.
        """
        words = cls.frame_to_words(frame)
        lines = [
            "; Сгенерировано sm2_dks_bridge.py — кадр {}".format(frame.name),
            "; Слова кадра DKS в памяти СМ-2 и регистре SM2KD.",
            "SET CPU SM2",
        ]
        if sc is not None:
            # Это код выборки устройства на шине СМ-2 (по умолчанию 020),
            # а не номер канала КРК Э-60 — их нельзя путать.
            lines.append("SET SM2K SC={:03o}".format(sc))
        lines.extend(cls.deposit_commands(words, base))
        lines.append("; Выгрузка первого слова в регистр данных линии 2К")
        lines.extend(cls.sm2k_commands(words[0]))
        lines.append("QUIT")
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Команды CLI
# ---------------------------------------------------------------------------

def run_selftest(log) -> int:
    """Прогнать PING + WRITE + READ через встроенный эмулятор протокола."""
    server = LoopbackDksServer(log=log)
    port = server.start()
    try:
        log("Поднят хостовый эмулятор протокола на порту {}".format(port))
        with DksLink("127.0.0.1", port, log=log) as link:
            reply = link.ping()
            assert reply.op == OP_PING and reply.name == "PING"
            log("PING: квитирование получено")

            link.write(CELL_REQUEST, 0o400)
            got = link.read(CELL_REQUEST)
            if got != 0o400:
                raise DksProtocolError(
                    "WRITE/READ: записано {:o}, прочитано {:o}".format(0o400, got))
            log("WRITE/READ ячейки 0154: записано {:o}, прочитано {:o}".format(
                0o400, got))

            frame = DksFrame(OP_WRITE, chan=2, addr=CELL_REQUEST, val=0o400)
            words = Sm2KAdapter.frame_to_words(frame)
            restored = Sm2KAdapter.words_to_frame(words)
            if restored.to_request() != frame.to_request():
                raise DksProtocolError("преобразование кадр ↔ слова СМ-2 не сходится")
            log("Кадр ↔ слова СМ-2: круговой тест пройден")
    finally:
        server.stop()
    log("СЕЛФТЕСТ: ПРОЙДЕН")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Минимальный мост СМ-2 ↔ Э-60 (кадры DKS D6/D7)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="адрес сервера pdp11_dks.c (по умолчанию 127.0.0.1)")
    parser.add_argument("--port", type=int, default=4140,
                        help="порт SET DKS BRIDGE (по умолчанию 4140)")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="таймаут ответа в секундах")
    parser.add_argument("--loopback", action="store_true",
                        help="работать через встроенный эмулятор протокола")
    parser.add_argument("--log", metavar="FILE",
                        help="писать лог «отправлено/получено» в файл")
    parser.add_argument("--sm2-ini", metavar="FILE",
                        help="записать SIMH-скрипт с DEPOSIT-ами кадра в СМ-2")
    parser.add_argument("--sm2-sc", type=int, metavar="ОКТАЛЬНОЕ",
                        help="код выборки SM2K на шине СМ-2 (по умолчанию 020, "
                             "не путать с каналом КРК)")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("selftest", help="проверить формат кадра и квитирование")
    sub.add_parser("ping", help="кадр 04 PING")
    p_write = sub.add_parser("write", help="кадр 02 WRITE")
    p_write.add_argument("--addr", required=True, help="адрес words, восьмеричный")
    p_write.add_argument("--val", required=True, help="слово, восьмеричное")
    p_write.add_argument("--chan", type=int, default=2, help="канал КРК 0..3")
    p_read = sub.add_parser("read", help="кадр 01 READ")
    p_read.add_argument("--addr", required=True, help="адрес words, восьмеричный")
    p_read.add_argument("--chan", type=int, default=2, help="канал КРК 0..3")

    args = parser.parse_args(argv)
    command = args.command or "selftest"

    log_file = None
    if args.log:
        log_file = open(args.log, "w", encoding="utf-8")

    def log(text):
        print(text)
        if log_file is not None:
            log_file.write(text + "\n")
            log_file.flush()

    try:
        if command == "selftest":
            return run_selftest(log)

        server = None
        host, port = args.host, args.port
        if args.loopback:
            server = LoopbackDksServer(log=log)
            port = server.start()
            host = "127.0.0.1"
            log("Поднят хостовый эмулятор протокола на порту {}".format(port))
        try:
            with DksLink(host, port, timeout=args.timeout, log=log) as link:
                if command == "ping":
                    link.ping()
                elif command == "write":
                    frame = DksFrame(OP_WRITE, chan=args.chan,
                                     addr=int(args.addr, 8),
                                     val=int(args.val, 8))
                    link.transaction(frame)
                    if args.sm2_ini:
                        with open(args.sm2_ini, "w", encoding="utf-8") as handle:
                            handle.write(Sm2KAdapter.build_ini(
                                frame, sc=args.sm2_sc))
                        log("SIMH-скрипт записан: " + args.sm2_ini)
                elif command == "read":
                    value = link.read(int(args.addr, 8), chan=args.chan)
                    log("РЕЗУЛЬТАТ READ[{:06o}] = {:06o}".format(
                        int(args.addr, 8), value))
                else:
                    parser.error("неизвестная команда " + command)
        finally:
            if server is not None:
                server.stop()
        log("ОБМЕН: ЗАВЕРШЁН")
        return 0
    except (DksProtocolError, DksTimeout, OSError) as exc:
        log("ОШИБКА: " + str(exc))
        return 1
    finally:
        if log_file is not None:
            log_file.close()


if __name__ == "__main__":
    sys.exit(main())
