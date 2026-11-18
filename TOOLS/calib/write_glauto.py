#!/usr/bin/env python3
"""Записать SRC/GLAUTO.FTN по коэффициентам из best.json.

Использование:
  python3 TOOLS/calib/write_glauto.py [best.json]
Без аргумента читает best.json рядом со скриптом.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
src = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'best.json'
data = json.loads(src.read_text())
p = data['params']

out = '''C==============================================================
C     ГЛИССАДА-6. АВТОПИЛАТ ЗАХОДА (РЕЖИМ 1).
C     КОЭФФИЦИЕНТЫ ПОДОБРАНЫ ПРИ РЕАЛЬНЫХ ТТХ ИЗ SRC/GLTTX.FTN
C     СЦЕНАРИЙ: KTIP=1..5, SIGW=1.5, RSEED=7351, DT0=0.60.
C     СМ. DOCS/ANALYSIS/TTX-AUDIT.MD И TOOLS/CALIB/.
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


def fmt(v):
    return ('%g' % v) if not isinstance(v, str) else v


for lab, row in zip((100, 200, 300, 400, 500), p):
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
      END
'''
# Второй END в шаблоне выше удаляем: одна подпрограмма
out = out.replace('      RETURN\n      END\n      END\n', '      RETURN\n      END\n')
target = REPO / 'SRC' / 'GLAUTO.FTN'
target.write_text(out, encoding='utf-8')
bad = [(i, len(l)) for i, l in enumerate(out.split('\n'), 1) if len(l) > 72]
if bad:
    raise SystemExit('строки >72: %s' % bad[:5])
print('записано', target, 'строк', out.count('\n'))
