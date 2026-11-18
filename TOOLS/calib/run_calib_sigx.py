#!/usr/bin/env python3
"""Калибровка GLAUTO: один прогон = метрики для всех пяти типов.

Использование:
  python3 run_calib.py '<json-список параметров>' [рабочий_каталог]
Параметры по типам: [GE, GEW, OFF, HFL, VYF, KV, KD].
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
import os
SIG = float(os.environ.get('CALIB_SIG','1.5'))
REPO = HERE.parent.parent
SRC = REPO / 'SRC'
BT = '/home/azizz/Yandex.Disk/dispak/build/besmtool/besmtool'
DISPAK_DIR = '/home/azizz/Yandex.Disk/rezerv/build/dispak'
PTY = '/home/azizz/Yandex.Disk/besm-crypto/work/run_save_pty.py'

DEFAULT = [
    [0.50, 0.08,   0, 30, -0.5, 0.040, 0.5],
    [0.50, 0.08, -18, 40, -0.4, 0.060, 0.5],
    [0.50, 0.08,   0, 12, -0.7, 0.025, 0.5],
    [0.20, 0.20, -20, 30, -0.5, 0.040, 0.5],
    [0.20, 0.08, -30,  4, -0.5, 0.040, 0.5],
]


def gost(text):
    return (text.replace('ё', 'Е').replace('Ё', 'Е')
                .replace('«', '"').replace('»', '"')
                .replace('—', '-').replace('–', '-').upper())


def fmt(v):
    return ('%g' % v) if not isinstance(v, str) else v


def make_glauto(p):
    """Генерация GLAUTO.FTN по параметрам p (список из 5 строк)."""
    out = '''C==============================================================
C     ГЛИССАДА-6. АВТОПИЛАТ (КАЛИБРОВОЧНАЯ КОПИЯ).
C==============================================================
      SUBROUTINE GLAUTO(X,U)
      DIMENSION X(13),U(4)
      COMMON /SOST/ GM,S,BB,CC,CL0,CLA,CLMX,CD0,AK,CMA,CM0,CMDE,
     1CMQ,CLB,CLDA,CLP,CNB,CNDR,CNR,CYB,ETYPE,THMAX,PMAX,VTHR,HCR
      COMMON /VYVOD/ ALFA,BETA,QBAR,VA,RHO,THR,CLV,CDV
      COMMON /GLOB/ T,DTSHAG,KTIP,MODE,ICTRL,NFR,IFLIB,TMAX
      COMMON /BURJA/ WGX,WGY,WGZ,SIGW,TAU
      EGLI=X(13)+0.05241*X(11)
      GO TO (100,200,300,400,500),KTIP
'''
    labels = [100, 200, 300, 400, 500]
    for lab, row in zip(labels, p):
        ge, gew, off, hfl, vyf, kv, kd = row
        out += '  %d CONTINUE\n' % lab
        if off != 0:
            out += '      EGLI=EGLI+(%s)\n' % fmt(off)
        out += '      GE=%s\n' % fmt(ge)
        out += '      IF(SIGW.GT.0.) GE=%s\n' % fmt(gew)
        out += '      VYC=-0.05241*X(1)-GE*EGLI\n'
        out += '      IF(X(13).LT.HCR+(%s)) VYC=(%s)\n' % (fmt(hfl), fmt(vyf))
        out += '      DE=(%s)*(X(2)-VYC)-(%s)*X(10)\n' % (fmt(-kv), fmt(kd))
        out += '      GO TO 150\n'
    out += '''  150 CONTINUE
      IF(DE.GT.0.30) DE=0.30
      IF(DE.LT.-0.30) DE=-0.30
      U(1)=DE
      DTZ=0.35+2.0*(VTHR-X(1))/VTHR
      IF(DTZ.GT.1.) DTZ=1.
      IF(DTZ.LT.0.) DTZ=0.
      U(4)=DTZ
      DA=-0.0008*X(12)-0.02*X(3)-0.25*X(8)
      IF(DA.GT.0.15) DA=0.15
      IF(DA.LT.-0.15) DA=-0.15
      U(2)=DA
      DR=-1.0*X(9)+0.03*BETA
      IF(DR.GT.0.20) DR=0.20
      IF(DR.LT.-0.20) DR=-0.20
      U(3)=DR
      RETURN
      END
'''
    return out


def build(W, p):
    W.mkdir(parents=True, exist_ok=True)
    # диалоговые копии Fortran (WRITE убраны, метки сохранены)
    import importlib.util
    spec = importlib.util.spec_from_file_location('bd', REPO / 'TOOLS/build-dialog.py')
    bd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bd)
    names = ['GLTTX', 'GLINITD', 'GLPROIZ', 'GLAUTO', 'GLNUMR', 'GLOUT', 'GLACC']
    body = ''
    for n in names:
        if n == 'GLAUTO':
            text = make_glauto(p)
        else:
            text = bd.dialog_fortran(n)
        body += gost(text)
    kern = '''шифр 419999 зс5^
лен 40(2348-wr)^
ОЗУ 32^
АЦПУ 140^
ТРА 37^
eeв1а3
*name GLKERN
*call yesmemory
*perso:402700
*forex
''' + body + '''*to perso:402700
*end file
``````
еконец
'''
    (W / 'GLKERN.b6').write_text(kern, encoding='utf-8')
    calib = gost((HERE / 'CALIB.PAS').read_text().replace('SIGW:=1.5', 'SIGW:=%g' % SIG))
    deck = '''шифр 419999 зс5^
лен 40(2348)^
ОЗУ 32^
АЦПУ 140^
ТРА 37^
eeв1а3
*name CALIB
*call yesmemory
*perso:402700
*perso:402570,cont
*stand
*call *pascal
''' + calib + '''*execute
*end file
``````
еконец
'''
    (W / 'CALIB.b6').write_text(deck, encoding='utf-8')


def run(W):
    import os, subprocess
    env = dict(os.environ)
    env['BESM6_PATH'] = str(W)
    env['PATH'] = DISPAK_DIR + ':' + env['PATH']
    for deck in ('GLKERN.b6', 'CALIB.b6'):
        r = subprocess.run(['python3', PTY, deck, '240'], cwd=W, env=env,
                           capture_output=True, text=True, timeout=400)
        log = W / (deck.rsplit('.', 1)[0] + '.log')
        if 'ЕRR 0' in log.read_text(errors='ignore'):
            print('ОШИБКА компиляции ядра', file=sys.stderr)
            return None
    log = (W / 'CALIB.log').read_text(errors='ignore')
    rows = []
    for line in log.split('\n'):
        if not line.strip().startswith('999'):
            continue
        line = line.replace('Е', 'E').replace('Т', 'T').replace('Н', 'H')
        nums = re.findall(r'[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?', line)
        if len(nums) >= 6:
            rows.append((int(float(nums[0])), float(nums[1]), float(nums[2]),
                         float(nums[3]), int(float(nums[4])), int(float(nums[5]))))
    return rows


if __name__ == '__main__':
    p = json.loads(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    W = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(str(HERE / ('work-sig' + str(SIG))))
    W.mkdir(parents=True, exist_ok=True)
    if not (W / '2348').exists():
        import shutil
        shutil.copy('/usr/local/share/besm6/2348', W / '2348')
        for f in ('2048', '2053', '2063', '2086', '2099', '2113', '2148',
                  '2153', '2222', '2248', '4001'):
            src = Path('/usr/local/share/besm6') / f
            if src.exists():
                (W / f).symlink_to(src)
    build(W, p)
    rows = run(W)
    print('результат:', rows)
