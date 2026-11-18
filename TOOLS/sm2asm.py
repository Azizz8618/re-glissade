#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Минимальный ассемблер для эмулируемой СМ-2 (тренажёр «Глиссада-6»).

Поддерживает:
  * метки (LABEL: или LABEL в первом поле);
  * мнемоники базовой группы MRG и расширенные SM2_OP_*;
  * операнды: восьмеричные числа (по умолчанию), 0x... (шестнадцатеричные),
    0d... (десятичные), метки и простые выражения LABEL+N / LABEL-N;
  * комментарии, начинающиеся с ';' до конца строки;
  * директивы .ORG, .WORD, .END.

Результат работы:
  * SIMH-скрипт (.ini): SET CPU SM2, DEPOSIT-ы, DEPOSIT P, RUN, EXAMINE, QUIT;
  * текстовый дамп слов (адрес -> слово) для проверки.

Использование:
  python3 TOOLS/sm2asm.py TOOLS/sm2_tasks/ps1.asm -o /tmp/ps1.ini
  python3 TOOLS/sm2asm.py TOOLS/sm2_tasks/ps1.asm -o /tmp/ps1.ini \
      --dump /tmp/ps1.map --start START --examine OUT

Все адреса и слова выводятся в восьмеричной системе, как того ожидает SIMH.
"""

import argparse
import os
import re
import sys


class AssemblerError(Exception):
    """Ошибка сборки с указанием номера строки исходника."""

    def __init__(self, line_no, message):
        super().__init__("строка {}: {}".format(line_no, message))
        self.line_no = line_no
        self.message = message


# --- Таблицы кодировок (взяты из HP2100/hp2100_sys.c и sm2_params.h) --------

# Базовые команды MRG. MRG opcode mask = 0074000, opcode shift = 11.
# Адресное поле занимает разряды 0-8 (0000777).
MRG_OPS = {
    "AND": 0o010000,
    "JSB": 0o014000,
    "XOR": 0o020000,
    "JMP": 0o024000,
    "IOR": 0o030000,
    "ISZ": 0o034000,
    "ADA": 0o040000,
    "ADB": 0o044000,
    "CPA": 0o050000,
    "CPB": 0o054000,
    "LDA": 0o060000,
    "LDB": 0o064000,
    "STA": 0o070000,
    "STB": 0o074000,
}

# Команда останова из IOG-таблицы (канонический HLT без select code).
HLT_OP = 0o102000

# Расширенные команды СМ-2. В эмуляторе SM2_OP(IR) = IR & 0177777,
# поэтому слово команды должно в точности равняться коду из таблицы.
SM2_OPS = {
    "DLD": 0o001100,  # двойная загрузка
    "DST": 0o001200,  # двойная запись
    "MPY": 0o000100,  # умножение целых
    "DIV": 0o000200,  # деление целых
    "LDX": 0o001104,  # загрузка РИ1
    "LDY": 0o001105,  # загрузка РИ2
    "STX": 0o001204,  # запись РИ1
    "STY": 0o001205,  # запись РИ2
    "LBN": 0o001101,  # загрузка РБ1
    "LBP": 0o001102,  # подготовка РБ2
    "FAD": 0o001400,  # сложение с плавающей точкой
    "FSB": 0o001410,  # вычитание с плавающей точкой
    "FMP": 0o001420,  # умножение с плавающей точкой
    "FDV": 0o001430,  # деление с плавающей точкой
    "TAS": 0o001107,  # проверка и установка разряда
    "FIX": 0o0105100,  # float -> int
    "FLT": 0o0105120,  # int -> float
    "ASR": 0o000011,  # арифметический сдвиг вправо
    "ASL": 0o000001,  # арифметический сдвиг влево
    "LSR": 0o000012,  # логический сдвиг вправо
    "LSL": 0o000002,  # логический сдвиг влево
    "RRR": 0o000014,  # циклический сдвиг вправо
    "RRL": 0o000004,  # циклический сдвиг влево
}

# Команды сдвига в текущей реализации эмулятора занимают одно слово:
# счётчик сдвига берётся из разрядов 12-15 IR, а PR увеличивается только
# на единицу. Остальные расширенные команды имеют второе слово (адрес
# или непосредственный операнд) и увеличивают PR на два.
SHIFT_OPS = {"ASR", "ASL", "LSR", "LSL", "RRR", "RRL"}

DIRECTIVES = {".ORG", ".WORD", ".END"}

WORD_MASK = 0o177777       # 16-разрядное слово СМ-2 без старшего разряда IR
MRG_ADDR_MASK = 0o777      # адресное поле MRG: 9 разрядов
TOKEN_RE = re.compile(
    r"[+-]|0[xX][0-9a-fA-F]+|0[dD][0-9]+|[0-9]+|[A-Za-z_][A-Za-z0-9_]*"
)


def op_size(mnemonic, line_no):
    """Вернуть количество слов, занимаемых командой."""
    name = mnemonic.upper()
    if name in MRG_OPS or name == "HLT" or name in SHIFT_OPS:
        return 1
    if name in SM2_OPS:
        return 2
    raise AssemblerError(line_no, "неизвестная мнемоника «{}»".format(mnemonic))


def is_known_op(token):
    """Проверить, является ли токен мнемоникой или директивой."""
    if token is None:
        return False
    upper = token.upper()
    return upper in MRG_OPS or upper in SM2_OPS or upper == "HLT" or upper in DIRECTIVES


def parse_line(text, line_no):
    """Разобрать одну строку. Вернуть (label, op, operands) или None."""
    code = text.split(";", 1)[0].strip()
    if not code:
        return None

    tokens = code.split()
    label = None

    # Метка с двоеточием: LABEL: OP ...
    if tokens[0].endswith(":"):
        label = tokens[0][:-1]
        tokens = tokens[1:]
    # Метка без двоеточия: LABEL  OP ... (второе слово — мнемоника/директива)
    elif len(tokens) > 1 and not is_known_op(tokens[0]) and is_known_op(tokens[1]):
        label = tokens[0]
        tokens = tokens[1:]

    if not tokens:
        if label is None:
            raise AssemblerError(line_no, "пустая строка после удаления метки")
        return (label, ".NONE", [])

    op = tokens[0].upper()
    operands = []
    if len(tokens) > 1:
        rest = " ".join(tokens[1:])
        operands = [p.strip() for p in rest.split(",") if p.strip()]

    if label is not None and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", label):
        raise AssemblerError(line_no, "неверное имя метки «{}»".format(label))

    if op not in DIRECTIVES and op not in MRG_OPS and op not in SM2_OPS and op != "HLT":
        raise AssemblerError(line_no, "неизвестная мнемоника «{}»".format(tokens[0]))

    if op in MRG_OPS:
        if len(operands) != 1:
            raise AssemblerError(line_no, "команда {} требует один операнд".format(op))
    if op == "HLT":
        if operands:
            raise AssemblerError(line_no, "команда HLT не имеет операнда")
    elif op in SM2_OPS and op not in SHIFT_OPS:
        if len(operands) != 1:
            raise AssemblerError(line_no, "команда {} требует один операнд".format(op))
    elif op in SHIFT_OPS:
        if operands:
            raise AssemblerError(line_no, "команда {} не имеет операнда в текущей кодировке".format(op))
    elif op == ".ORG":
        if len(operands) != 1:
            raise AssemblerError(line_no, "директива .ORG требует один операнд")
    elif op == ".WORD":
        if not operands:
            raise AssemblerError(line_no, "директива .WORD требует хотя бы один операнд")

    return (label, op, operands)


def eval_expr(text, labels, line_no):
    """Вычислить простое выражение вида LABEL+N, 0010, 0x20, 0d10."""
    compact = text.replace(" ", "").replace("\t", "")
    if not compact:
        raise AssemblerError(line_no, "пустое выражение")

    matches = list(TOKEN_RE.finditer(compact))
    if not matches or "".join(m.group(0) for m in matches) != compact:
        raise AssemblerError(line_no, "неверное выражение «{}»".format(text))

    sign = 1
    value = 0
    for match in matches:
        token = match.group(0)
        if token == "+":
            sign = 1
            continue
        if token == "-":
            sign = -1
            continue
        if token.lower().startswith("0x"):
            try:
                term = int(token, 16)
            except ValueError:
                raise AssemblerError(line_no, "неверное число «{}»".format(token))
        elif token.lower().startswith("0d"):
            try:
                term = int(token[2:], 10)
            except ValueError:
                raise AssemblerError(line_no, "неверное число «{}»".format(token))
        elif token[0].isdigit():
            try:
                term = int(token, 8)
            except ValueError:
                raise AssemblerError(line_no, "неверное восьмеричное число «{}»".format(token))
        else:
            if token not in labels:
                raise AssemblerError(line_no, "неизвестная метка «{}»".format(token))
            term = labels[token]
        value += sign * term
        sign = 1
    return value


def assemble(source_text):
    """Собрать исходник. Вернуть (words, labels, start_addr).

    words — список пар (адрес, слово).
    """
    records = []
    for line_no, raw in enumerate(source_text.splitlines(), 1):
        parsed = parse_line(raw, line_no)
        if parsed is not None:
            records.append((line_no, parsed[0], parsed[1], parsed[2]))

    # --- Первый проход: адреса меток ---
    labels = {}
    address = 0
    start_addr = None
    for line_no, label, op, operands in records:
        if op == ".ORG":
            address = eval_expr(operands[0], labels, line_no)
        if label is not None:
            if label in labels:
                raise AssemblerError(line_no, "повторное определение метки «{}»".format(label))
            labels[label] = address
        if op in (".NONE", ".END", ".ORG"):
            continue
        if start_addr is None:
            start_addr = address
        if op == ".WORD":
            address += len(operands)
        else:
            address += op_size(op, line_no)

    # --- Второй проход: генерация слов ---
    words = []
    address = 0
    for line_no, label, op, operands in records:
        if op == ".ORG":
            address = eval_expr(operands[0], labels, line_no)
            continue
        if op in (".NONE", ".END"):
            continue

        if op == ".WORD":
            for operand in operands:
                value = eval_expr(operand, labels, line_no)
                check_word(value, line_no)
                words.append((address, value))
                address += 1
            continue

        if op == "HLT":
            emit(words, address, HLT_OP, line_no)
            address += 1
            continue

        if op in MRG_OPS:
            target = eval_expr(operands[0], labels, line_no)
            if target < 0 or target > MRG_ADDR_MASK:
                raise AssemblerError(
                    line_no,
                    "адрес {:o} вне адресного поля MRG (000000-000777)".format(target),
                )
            emit(words, address, MRG_OPS[op] | (target & MRG_ADDR_MASK), line_no)
            address += 1
            continue

        # Расширенные команды СМ-2
        code = SM2_OPS[op]
        emit(words, address, code, line_no)
        address += 1
        if op in SHIFT_OPS:
            # Операнда нет: эмулятор берёт счётчик из разрядов 12-15 IR.
            continue
        operand = eval_expr(operands[0], labels, line_no)
        check_word(operand, line_no)
        emit(words, address, operand, line_no)
        address += 1

    if start_addr is None:
        raise AssemblerError(0, "в исходнике нет команд или данных")
    return words, labels, start_addr


def check_word(value, line_no):
    """Проверить, что значение помещается в 16-разрядное слово."""
    if value < 0 or value > WORD_MASK:
        raise AssemblerError(
            line_no, "значение {:o} не помещается в слово СМ-2".format(value)
        )


def emit(words, address, value, line_no):
    check_word(value, line_no)
    if words and words[-1][0] >= address:
        raise AssemblerError(line_no, "пересечение адресов при сборке")
    words.append((address, value))


def resolve(text, labels, default):
    """Разрешить имя метки или восьмеричное число."""
    if text is None:
        return default
    if text in labels:
        return labels[text]
    try:
        return int(text, 8)
    except ValueError:
        raise AssemblerError(0, "неизвестный адрес «{}»".format(text))


def write_ini(path, words, start_addr, examine_addr, source_name):
    """Записать SIMH-скрипт."""
    lines = [
        "; Сгенерировано sm2asm.py на основе {}".format(source_name),
        "; Адреса и слова — восьмеричные (SIMH по умолчанию).",
        "SET CPU SM2",
    ]
    for address, value in words:
        lines.append("DEPOSIT {:06o} {:06o}".format(address, value))
    lines.append("DEPOSIT P {:05o}".format(start_addr))
    lines.append("RUN")
    if examine_addr is not None:
        lines.append("EXAMINE {:06o}".format(examine_addr))
    lines.append("QUIT")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def write_dump(path, words, source_name):
    """Записать текстовый дамп слов."""
    lines = [
        "; Дамп слов, сгенерирован из {}".format(source_name),
        "; Адрес     Слово",
    ]
    for address, value in words:
        lines.append("{:06o}    {:06o}".format(address, value))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Минимальный ассемблер СМ-2 для тренажёра «Глиссада-6»"
    )
    parser.add_argument("source", help="исходник на языке ассемблера СМ-2")
    parser.add_argument("-o", "--output", help="путь к SIMH-скрипту (.ini)")
    parser.add_argument("--dump", help="путь к текстовому дампу слов (.map)")
    parser.add_argument("--start", help="метка или восьмеричный адрес запуска")
    parser.add_argument("--examine", help="метка или адрес для EXAMINE")
    args = parser.parse_args(argv)

    source_path = args.source
    try:
        with open(source_path, "r", encoding="utf-8") as handle:
            source_text = handle.read()
    except OSError as exc:
        print("ошибка чтения {}: {}".format(source_path, exc), file=sys.stderr)
        return 2

    try:
        words, labels, start_addr = assemble(source_text)
    except AssemblerError as exc:
        print("{}: {}".format(source_path, exc), file=sys.stderr)
        return 1

    if args.start is not None:
        start_addr = resolve(args.start, labels, start_addr)
    examine_addr = None
    if args.examine is not None:
        examine_addr = resolve(args.examine, labels, None)
    elif "OUT" in labels:
        examine_addr = labels["OUT"]

    base = os.path.splitext(os.path.basename(source_path))[0]
    ini_path = args.output or (base + ".ini")
    # По умолчанию дамп лежит рядом со скриптом, чтобы не мусорить
    # в рабочем каталоге.
    dump_path = args.dump or os.path.join(
        os.path.dirname(ini_path) or ".", base + ".map"
    )

    write_ini(ini_path, words, start_addr, examine_addr, os.path.basename(source_path))
    write_dump(dump_path, words, os.path.basename(source_path))

    print("Собрано слов: {}".format(len(words)))
    print("SIMH-скрипт: {}".format(ini_path))
    print("Дамп слов:   {}".format(dump_path))
    print("Запуск:      {:06o}".format(start_addr))
    if examine_addr is not None:
        print("EXAMINE:     {:06o}".format(examine_addr))
    return 0


if __name__ == "__main__":
    sys.exit(main())
