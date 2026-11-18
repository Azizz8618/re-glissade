#!/usr/bin/env python3
"""Ручная игра в режиме ТЕЛЕ.

Запускает колоду JOB/GLCALL-2700.B6 на псевдотерминале и передаёт ввод
пользователя прямо в задание. Ответы на `WHAT=` и приглашения PASRED
вводятся вручную, как на настоящем терминале.

    python3 TOOLS/play.py [колода]

По умолчанию — JOB/GLCALL-2700.B6. Для выхода — Ctrl-C.
"""
import os
import pty
import select
import subprocess
import sys
import termios
import tty
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DECK = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'JOB' / 'GLCALL-2700.B6'
WORK = Path('/tmp/.private/azizz/opencode/play')
WORK.mkdir(parents=True, exist_ok=True)
(WORK / DECK.name).write_text(DECK.read_text(encoding='utf-8'), encoding='utf-8')

env = dict(os.environ)
env['BESM6_PATH'] = str(Path.home() / '.besm6') + ':/usr/local/share/besm6'
env['PATH'] = '/home/azizz/Yandex.Disk/rezerv/build/dispak:' + env.get('PATH', '')

master, slave = pty.openpty()
proc = subprocess.Popen(['dispak', '-p', DECK.name], cwd=WORK,
                        stdin=slave, stdout=slave, stderr=slave,
                        env=env, close_fds=True)
os.close(slave)

try:
    old = termios.tcgetattr(sys.stdin.fileno())
    tty.setraw(sys.stdin.fileno())
except (termios.error, OSError, ValueError):
    old = None
try:
    while True:
        ready, _, _ = select.select([master, sys.stdin], [], [], 0.5)
        for fd in ready:
            try:
                data = os.read(fd if fd != sys.stdin else sys.stdin.fileno(), 4096)
            except OSError:
                data = b''
            if not data:
                continue
            if fd == master:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            else:
                os.write(master, data)
        if proc.poll() is not None:
            break
finally:
    if old is not None:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    os.close(master)
print('\nЗадача завершена, код:', proc.returncode)
