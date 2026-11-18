#!/usr/bin/env python3
"""Прогон недиалоговой деки (запись модулей в библиотеку 2348) под pty.

Запускает `dispak -p <deck>`, отвечает переводом строки на каждое
приглашение WНАТ= (терминальный ввод монитора/компилятора) и пишет лог.

    python3 work/run_save_pty.py work/par203_save.b6 [таймаут_сек]

Лог: <deck без .b6>.log (пишется на лету, остаётся и при таймауте).
"""
import os
import pty
import select
import subprocess
import sys
import time

DECK = sys.argv[1]
TIMEOUT = int(sys.argv[2]) if len(sys.argv) > 2 else 900
LOG = DECK[:-3] + '.log' if DECK.endswith('.b6') else DECK + '.log'

env = dict(os.environ)

master, slave = pty.openpty()
cmd = ['dispak'] + os.environ.get('DISPAK_EXTRA', '').split() + ['-p', DECK]
proc = subprocess.Popen(cmd, stdin=slave, stdout=slave,
                        stderr=slave, env=env, close_fds=True)
os.close(slave)

buf = b''
what_sent = 0
deadline = time.time() + TIMEOUT
MAXOUT = 4 * 1024 * 1024
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
        if len(buf) <= MAXOUT:
            progress.write(chunk)
            progress.flush()
        text = buf.decode('utf-8', 'ignore')
        nwhat = text.count('WНАТ=')
        if nwhat > what_sent:
            for _ in range(nwhat - what_sent):
                os.write(master, b'L0\n' if what_sent == 0 else b'\n')
            what_sent = nwhat
    if proc.poll() is not None:
        time.sleep(0.5)
        try:
            while True:
                chunk = os.read(master, 4096)
                if not chunk:
                    break
                buf += chunk
                if len(buf) <= MAXOUT:
                    progress.write(chunk)
        except OSError:
            pass
        break

progress.close()
rc = None
try:
    rc = proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.kill()
    proc.wait()
    print('!!! ТАЙМАУТ', file=sys.stderr)
os.close(master)

text = buf.decode('utf-8', 'ignore')
print('WНАТ отвечено: %d, выход: %s' % (what_sent, rc),
      file=sys.stderr)
if 'КОНЕЦ ЗАДАЧИ' in text:
    print('задача завершилась штатно', file=sys.stderr)
else:
    print('!!! ЗАДАЧА НЕ ЗАВЕРШИЛАСЬ ШТАТНО', file=sys.stderr)
sys.exit(0 if rc == 0 and 'КОНЕЦ ЗАДАЧИ' in text else 1)
