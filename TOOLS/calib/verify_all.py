#!/usr/bin/env python3
"""Проверка всех пяти типов через диалоговую игру из PERSO.

Запускается после установки: TOOLS/install-2348.sh 0.
Для каждого типа запускает CALLGL-колоду с нужным ответом TIP и
печатает последние VERT/OCENKA из лога.
"""
import os
import pty
import re
import select
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DECK = REPO / 'JOB' / 'GLCALL-2700.B6'
WORK = Path('/tmp/.private/azizz/opencode/verify-all')
WORK.mkdir(parents=True, exist_ok=True)
(WORK / 'GLCALL-2700.B6').write_text(DECK.read_text(encoding='utf-8'), encoding='utf-8')

NAMES = {1: 'МиГ-15', 2: 'Ил-28', 3: 'Ту-104', 4: 'Ан-24', 5: 'Ан-2'}
SIGW = sys.argv[1] if len(sys.argv) > 1 else '1.5'


def run(tip):
    answers = [str(tip), '1', '0', '5', '0', '2400', '7351', SIGW, '0.60', 'STA', 'EXIT']
    master, slave = pty.openpty()
    env = dict(os.environ)
    env['BESM6_PATH'] = str(Path.home() / '.besm6') + ':/usr/local/share/besm6'
    proc = subprocess.Popen(['dispak', '-p', 'GLCALL-2700.B6'], cwd=WORK,
                            stdin=slave, stdout=slave, stderr=slave,
                            env=env, close_fds=True)
    os.close(slave)
    buf = b''
    sent = 0
    what = 0
    deadline = time.time() + 240
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
            text = buf.decode('utf-8', 'ignore')
            n = text.count('WНАТ=')
            if n > what:
                for _ in range(n - what):
                    os.write(master, b'\n')
                what = n
            np = text.count('\n-\r')
            while sent < len(answers) and np > sent:
                os.write(master, (answers[sent] + '\n').encode())
                sent += 1
        if proc.poll() is not None:
            break
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    os.close(master)
    text = buf.decode('utf-8', 'ignore').replace('Е', 'E')
    verts = re.findall(r'VERT=\s*([-\d.E+]+)', text)
    oces = re.findall(r'OCENKA=\s*(\d+)', text)
    return (verts[-1] if verts else '?', oces[-1] if oces else '?',
            'КОНЕЦ ЗАДАЧИ' in text, sent)


for tip in (1, 2, 3, 4, 5):
    v, o, ok, n = run(tip)
    print('SIGW=%s тип %d (%s): VERT=%s OCENKA=%s ответов=%d'
          % (SIGW, tip, NAMES[tip], v, o, n), flush=True)
