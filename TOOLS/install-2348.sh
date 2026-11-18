#!/bin/sh
# Установка диалоговой Глиссады в PERSO зоны 2700(8) тома ~/.besm6/2348.
#
# Что делает:
#   1. резервная копия ~/.besm6/2348 с таймштампом;
#   2. колода JOB/GLKERN-2700.B6  - Fortran-ядро -> *to perso:402700;
#   3. колода JOB/GLDIAL-2700.B6  - Pascal-оболочка -> та же зона;
#   4. проверка каталога зоны 2700 (besmtool view);
#   5. колода JOB/GLCALL-2700.B6  - контрольный вызов по имени (опционально).
#
# Диски: 2348 берётся из ~/.besm6 (первый путь), системный 2048 и прочие
# тома - из /usr/local/share/besm6 (второй путь).
#
# Запуск:  TOOLS/install-2348.sh [с-контрольным-вызовом=0|1]
# По умолчанию 1 - после записи выполняется прогон CALLGL.b6 под pty.
#
# ВАЖНО:Dispак зависает на приглашении WНАТ=, поэтому все колоды идут
# через pty-обвязку TOOLS/run_gldial_pty.py.

set -eu

REPO=$(cd "$(dirname "$0")/.." && pwd)
JOB="$REPO/JOB"
TOOLS="$REPO/TOOLS"
VOLS="$HOME/.besm6/2348"
DISPAK=${DISPAK:-/home/azizz/Yandex.Disk/rezerv/build/dispak/dispak}
BESTOOL=${BESTOOL:-/home/azizz/Yandex.Disk/dispak/build/besmtool/besmtool}
PATH=$(dirname "$DISPAK"):$PATH
export PATH
export BESM6_PATH="$HOME/.besm6:/usr/local/share/besm6"

DO_CALL=${1:-1}

[ -f "$VOLS" ] || { echo "СТОП: нет $VOLS" >&2; exit 1; }
[ -x "$DISPAK" ] || { echo "СТОП: нет $DISPAK" >&2; exit 1; }
[ -x "$BESTOOL" ] || { echo "СТОП: нет $BESTOOL" >&2; exit 1; }
for f in GLKERN-2700.B6 GLDIAL-2700.B6 GLCALL-2700.B6; do
    [ -f "$JOB/$f" ] || { echo "СТОП: нет $JOB/$f" >&2; exit 1; }
done

STAMP=$(date +%Y%m%d-%H%M%S)
BAK="$VOLS.bak-before-dialog-2700-$STAMP"
cp "$VOLS" "$BAK"
echo "Резервная копия: $BAK"

W=$(mktemp -d)
trap 'rm -rf "$W"' EXIT
cp "$JOB"/*.B6 "$W"/
cp "$TOOLS/run_gldial_pty.py" "$W"/
cd "$W"

echo "--- 1) Fortran-ядро -> PERSO зона 2700(8)"
python3 run_gldial_pty.py GLKERN-2700.B6 240
grep -a 'ДЛИНА LIВRАRУ' GLKERN-2700.log | tail -1
grep -ac 'ЕRR 0' GLKERN-2700.log | sed 's/^/Ошибок компиляции: /'

echo "--- 2) Pascal-оболочка -> та же зона 2700(8)"
python3 run_gldial_pty.py GLDIAL-2700.B6 240
grep -a 'ДЛИНА LIВRАRУ' GLDIAL-2700.log | tail -1
grep -ac 'БЫЛИ ОШИБКИ' GLDIAL-2700.log | sed 's/^/Ошибок трансляции: /'

echo "--- 3) Каталог зоны 2700(8)"
BESM6_PATH="$HOME/.besm6" "$BESTOOL" view 2348 --start=1472 --last=1472 \
    --encoding=t | sed -n '2,7p'

if [ "$DO_CALL" = 1 ]; then
    echo "--- 4) Контрольный вызов gldial из PERSO"
    python3 run_gldial_pty.py GLCALL-2700.B6 240
    grep -a 'OCENKA= \|EXIT\|КОНЕЦ ЗАДАЧИ' GLCALL-2700.log | tail -3
    if grep -aq 'OCENKA= 3' GLCALL-2700.log && grep -aq 'КОНЕЦ ЗАДАЧИ' GLCALL-2700.log; then
        echo "ПРОВЕРКА ПРОЙДЕНА: OCENKA= 3, штатное завершение"
    else
        echo "СТОП: контрольный вызов не дал OCENKA= 3" >&2
        exit 1
    fi
fi

echo "Готово. Записано в $VOLS, зона 2700(8)."
