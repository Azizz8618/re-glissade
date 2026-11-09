# Проверка колод ФОРТРАН ИПМ: колонки, продолжения, счёт Холлерита
import re, sys, glob, os

BASE = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/download/glissada6"
errors = []

def check_ftn(path):
    is_dat = path.endswith(".DAT")
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for num, line in enumerate(lines, 1):
        if is_dat:
            if len(line) > 80:
                errors.append(f"{path}:{num}: карта длиннее 80 ({len(line)})")
            continue
        # пустая карта допустима
        if line.strip() == "":
            if len(line) > 72:
                errors.append(f"{path}:{num}: строка длиннее 72 ({len(line)})")
            continue
        if len(line) > 72:
            errors.append(f"{path}:{num}: строка длиннее 72 ({len(line)})")
        if "\t" in line:
            errors.append(f"{path}:{num}: табуляция запрещена")
        c1 = line[0]
        if c1 == "C":
            continue  # комментарий
        # метка: колонки 1-5
        label = line[0:5]
        if label.strip() and not label.strip().isdigit():
            errors.append(f"{path}:{num}: метка не число: '{label}'")
        # продолжение: колонка 6
        cont = line[5] if len(line) >= 6 else " "
        stmt_start = 6
        if cont != " ":
            if label.strip():
                errors.append(f"{path}:{num}: метка и продолжение одновременно")
            stmt_start = 6
        elif len(line) > 5 and line[5] != " ":
            pass
        stmt = line[6:72]
        # счёт Холлерита: nH + ровно n символов внутри этой же карты
        for m in re.finditer(r"(\d+)H", stmt):
            n = int(m.group(1))
            rest = stmt[m.end():]
            if len(rest) < n:
                errors.append(
                    f"{path}:{num}: Холлерит {n}H не помещается в карту "
                    f"(осталось {len(rest)}) - поле разорвано продолжением?")
    # данные: контроль ширины полей
    if path.endswith(".DAT"):
        for num, line in enumerate(lines, 1):
            if len(line.strip()) == 0:
                continue
            if len(line) % 8 != 0 and num > 2 or (num == 1 and len(line) != 25 and len(line.strip()) != 0):
                errors.append(f"{path}:{num}: ширина карты данных {len(line)} (ожидалось 25 или кратно 8)")

for p in sorted(glob.glob(os.path.join(BASE, "SRC", "*.FTN"))):
    check_ftn(p)
for p in sorted(glob.glob(os.path.join(BASE, "DATA", "*.DAT"))):
    check_ftn(p)

if errors:
    print("НАЙДЕНЫ ОШИБКИ:")
    for e in errors:
        print(" ", e)
    sys.exit(1)
print("ВСЕ КОЛОДЫ ПРОШЛИ ПРОВЕРКУ: колонки 1-72, продолжения, Холлерит")
