#!/usr/bin/env python3
"""Прогон диалоговой Глиссады под псевдотерминалом.

Прямой `dispak -p deck.b6` зависает на приглашении видеотона `WHAT=`:
по правилу видеотона пустая посылка означает «продолжить». PASRED
(диалог Паскаля) приглашает одиночной литерой `-` в начале строки.

Запуск:
    BESM6_PATH=<каталог-с-копией-2348> PATH=<dispak>:$PATH \
      python3 TOOLS/run_gldial_pty.py <дека.b6> [таймаут_сек]

Лог пишется в <дека>.log на лету (остаётся и при таймауте).
"""
import os
import pty
import select
import subprocess
import sys
import time

DECK = sys.argv[1] if len(sys.argv) > 1 else 'GLDIAL.b6'
TIMEOUT = int(sys.argv[2]) if len(sys.argv) > 2 else 240
LOG = DECK.rsplit('.', 1)[0] + '.log'

# Сценарий контрольного прогона (совпадает с RUNS/run-2026-11-17-clean):
#   KTIP=3 (Ту-104), MODE=1 (автопилот), ICTRL=0 (пакетный вывод),
#   NFR=5, IFLIB=0, TMAX=2400, RSEED=7351, SIGW=1.5, DT0=0.60.
ANSWERS = [
    '3',       # TIP
    '1',       # MODE: 1 = автопилот
    '0',       # ICTRL: 0 = без запросов во время полёта
    '5',       # NFR
    '0',       # IFLIB
    '2400',    # TMAX
    '7351',    # RSEED — обязательно передаётся в /SBSEED/ через GLSEED
    '1.5',     # SIGW
    '0.60',    # DT0
    'STA',     # команда: пуск
    'EXIT',    # команда: выход после посадки
]

env = dict(os.environ)
master, slave = pty.openpty()
proc = subprocess.Popen(['dispak', '-p', DECK], stdin=slave, stdout=slave,
                        stderr=slave, env=env, close_fds=True)
os.close(slave)

buf = b''
sent = 0
what_sent = 0
deadline = time.time() + TIMEOUT
progress = open(LOG, 'wb')

while time.time() < deadline:
    ready, _, _ = select.select([master], [], [], 0.5)
    if ready:
        try:
            chunk = os.read(master, 4096)
        except OSError:
            break
        if not chunk:
            break
        buf += chunk
        progress.write(chunk)
        progress.flush()
        text = buf.decode('utf-8', 'ignore')

        nwhat = text.count('WНАТ=')
        if nwhat > what_sent:
            for _ in range(nwhat - what_sent):
                os.write(master, b'\n')
            what_sent = nwhat

        nprompt = text.count('\n-\r')
        while sent < len(ANSWERS) and nprompt > sent:
            os.write(master, (ANSWERS[sent] + '\n').encode('utf-8'))
            sent += 1

    if proc.poll() is not None:
        time.sleep(0.5)
        try:
            while True:
                chunk = os.read(master, 4096)
                if not chunk:
                    break
                buf += chunk
                progress.write(chunk)
        except OSError:
            pass
        break

progress.close()
try:
    proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.kill()
    proc.wait()
os.close(master)
print('WHAT отвечено: %d, PASRED: %d/%d, код выхода: %s'
      % (what_sent, sent, len(ANSWERS), proc.returncode))
