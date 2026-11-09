#!/usr/bin/env python3
# Сборка .b6-заданий для пакетного эмулятора dispak из материалов
# репозитория re-glissade (SRC + DATA). Обёртка - как в тестах
# репозитория dispak (tests/forex/forex.b6): шифр/лен + *forex.
import sys, os

REPO = "/home/z/my-project/repos/re-glissade"
OUT = "/home/z/my-project/run"

MODULES = ["GLMAIN.FTN", "GLPROIZ.FTN", "GLINITD.FTN",
           "GLNUM.FTN", "GLAUTO.FTN", "GLOUT.FTN"]
# Резервный вариант (этап 0 п.4): GLNUM заменяется на GLNUMR
MODULES_R = ["GLMAIN.FTN", "GLPROIZ.FTN", "GLINITD.FTN",
             "GLNUMR.FTN", "GLAUTO.FTN", "GLOUT.FTN"]

HEADER = """шифр 419999 зс5^
лен 41(2048)^
eeв1а3
*name {name}
*call yesmemory
*full list
*forex
"""

FOOTER = """*end file
``````
еконец
"""

def read_lines(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines

def make_job(name, data_file, out_file, modules=MODULES):
    src = []
    for m in modules:
        src.extend(read_lines(os.path.join(REPO, "SRC", m)))
    data = read_lines(os.path.join(REPO, "DATA", data_file))
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(HEADER.format(name=name))
        for l in src:
            f.write(l + "\n")
        f.write("*execute\n")
        for l in data:
            f.write(l + "\n")
        f.write(FOOTER)
    print("сделано:", out_file, len(src), "карт источников,", len(data), "карт данных")

os.makedirs(OUT, exist_ok=True)
make_job("Glis1", "GLIS1.DAT", os.path.join(OUT, "glis1.b6"))
make_job("Glis2", "GLIS2.DAT", os.path.join(OUT, "glis2.b6"))
make_job("Glis1r", "GLIS1.DAT", os.path.join(OUT, "glis1r.b6"), MODULES_R)
make_job("Glis2r", "GLIS2.DAT", os.path.join(OUT, "glis2r.b6"), MODULES_R)
