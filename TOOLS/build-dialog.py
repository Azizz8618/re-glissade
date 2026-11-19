#!/usr/bin/env python3
"""Сборка диалоговой Глиссады в PERSO и колоды запуска.

Что делает:
  1. Готовит диалоговые копии Fortran-ядра: заменяет WRITE(6) на комментарии
     (печать ведёт Pascal), сохраняя метки Computed GOTO.
  2. Собирает колоду `GLKERN.b6`: *forex -> *to perso:40<Z> (ядро в PERSO).
  3. Собирает колоду `GLDIAL.b6`: *perso:<Z> + *perso:402570,cont
     (Pascal runtime) -> *call *pascal -> *execute.
  4. Проверяет длины строк (<=72 для Fortran и Pascal).

Использование:
    python3 TOOLS/build-dialog.py [рабочий_каталог] [зона_PERSO]
По умолчанию: /tmp/.private/azizz/opencode/glperso и зона 2700(8).

ВАЖНО: копия тома 2348 должна содержать PERSO-библиотеку в зоне 2570(8)
(Pascal runtime). Рабочая копия НЕ должна быть системным диском.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / 'SRC'
WORK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/.private/azizz/opencode/glperso')
ZONE = sys.argv[2] if len(sys.argv) > 2 else '2700'
LU = '40'                     # логический номер устройства с томом 2348
PERSOCARD = f'{LU}{ZONE}'      # например 402700 -> карта *perso:402700

CORE = ['GLTTX', 'GLGAIN', 'GLKM', 'GLFAULT', 'GLRECF', 'GLSCORE', 'GLKMA', 'GLINITD', 'GLPROIZ', 'GLAUTO', 'GLNUMR', 'GLOUT', 'GLACC', 'GLRELF', 'GLFUEL']


def gost(text: str) -> str:
    """ГОСТ-10859: верхний регистр и замена типографских литер."""
    return (text.replace('ё', 'Е').replace('Ё', 'Е')
                .replace('«', '"').replace('»', '"')
                .replace('—', '-').replace('–', '-').upper())


def dialog_fortran(name: str) -> str:
    """Диалоговая копия Fortran-исходника без WRITE(6)."""
    text = (SRC / f'{name}.FTN').read_text(encoding='utf-8')
    out: list[str] = []
    for line in text.split('\n'):
        # Сохранить метку оператора: '   10 WRITE...' -> '   10 CONTINUE'
        # (иначе Computed GOTO в INITD/JUDG переходит в comment).
        m = re.match(r'^[C ]?\s+(\d{2,5})\s+WRITE\(6', line)
        if m:
            out.append(f'  {m.group(1)} CONTINUE')
            continue
        if 'WRITE(6' in line and not line.lstrip().startswith('C'):
            out.append('C' + line[1:] if line else line)
            continue
        out.append(line)
    text = '\n'.join(out)
    # В INITD ветви GO TO (10..50),KTIP только печатают имя самолёта;
    # в диалоге это делает Pascal. Метки на CONTINUE ФОРЭК запрещает,
    # поэтому удаляем ветки целиком, оставляя RETURN.
    if name == 'GLINITD':
        lines = text.split('\n')
        res, i = [], 0
        while i < len(lines):
            if lines[i].strip().startswith('GO TO (10,20,30,40,50),KTIP'):
                while i < len(lines) and lines[i].strip() != 'END':
                    i += 1
                res.append('      RETURN')
                continue
            res.append(lines[i])
            i += 1
        text = '\n'.join(res)
    # В JUDG все ветви GO TO (10,20,30,40),K сходятся в 50: удалить блок.
    if name == 'GLOUT':
        lines = text.split('\n')
        res, i = [], 0
        while i < len(lines):
            if lines[i].strip() == 'GO TO (10,20,30,40),K':
                while i < len(lines) and lines[i].strip() != '50 CONTINUE':
                    i += 1
                continue
            res.append(lines[i])
            i += 1
        text = '\n'.join(res)
    return text


def check_len(name: str, text: str) -> None:
    bad = [(n, len(ln)) for n, ln in enumerate(text.split('\n'), 1) if len(ln) > 72]
    if bad:
        raise SystemExit(f'СТОП: {name}: строки >72 символов: {bad[:5]}')


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)

    # 1. Диалоговые копии Fortran
    body = ''
    for name in CORE:
        text = dialog_fortran(name)
        check_len(name + '.FTN', text)
        (WORK / f'{name}-DLG.FTN').write_text(text, encoding='utf-8')
        body += gost(text)

    # 2. Колода ядра -> PERSO
    kern = f'''шифр 419999 зс5^
лен {LU}(2348-wr)^
ОЗУ 32^
АЦПУ 140^
ТРА 37^
eeв1а3
*name GLKERN
*call yesmemory
*perso:{PERSOCARD}
*full list
*forex
{body}*to perso:{PERSOCARD}
*end file
``````
еконец
'''
    (WORK / 'GLKERN.b6').write_text(kern, encoding='utf-8')

    # 3. Колода диалога (Pascal + PERSO-ядро + runtime)
    dia = gost((SRC / 'GLDIAL.PAS').read_text(encoding='utf-8'))
    check_len('GLDIAL.PAS', dia)
    dlg = f'''шифр 419999 зс5^
лен {LU}(2348)^
ОЗУ 32^
АЦПУ 140^
ТРА 37^
ТЕЛЕ^
eeв1а3
*name GLDIAL
*call yesmemory
*perso:{PERSOCARD}
*perso:402570,cont
*stand
*call *pascal
{dia}*execute
*end file
``````
еконец
'''
    (WORK / 'GLDIAL.b6').write_text(dlg, encoding='utf-8')

    # 4. Колода записи Pascal в ту же PERSO-зону (без runtime в каталоге)
    perso_dlg = f'''шифр 419999 зс5^
лен {LU}(2348-wr)^
ОЗУ 32^
АЦПУ 140^
ТРА 37^
ТЕЛЕ^
eeв1а3
*name GLDIAL
*call yesmemory
*perso:{PERSOCARD}
*call *pascal
{dia}*to perso:{PERSOCARD}
*end file
``````
еконец
'''
    (WORK / 'GLDIAL-PERSO.b6').write_text(perso_dlg, encoding='utf-8')

    # 5. Колода вызова диалога из PERSO по имени
    call = f'''шифр 419999 зс5^
лен {LU}(2348)^
ОЗУ 32^
АЦПУ 140^
ТРА 37^
ТЕЛЕ^
eeв1а3
*name CALLGL
*call yesmemory
*perso:{PERSOCARD}
*perso:402570,cont
*no list
*call gldial
*end file
``````
еконец
'''
    (WORK / 'CALLGL.b6').write_text(call, encoding='utf-8')

    print(f'Каталог сборки: {WORK}')
    print(f'PERSO-зона: {ZONE}(8), карта *perso:{PERSOCARD}')
    print('Колоды: GLKERN.b6 (ядро), GLDIAL-PERSO.b6 (Pascal в PERSO),')
    print('        CALLGL.b6 (вызов), GLDIAL.b6 (компиляция+execute)')
    print('Дальше: см. docs/PLAN-DIALOG.md, раздел 9.')


if __name__ == '__main__':
    main()
