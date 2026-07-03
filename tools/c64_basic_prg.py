#!/usr/bin/env python3
"""Tokenize ASCII BASIC source into a C64 PRG.

The tokenizer is intentionally small and deterministic. It avoids relying on
VICE key injection or petcat's source-case conventions when generating test
programs.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


BASIC_V2_TOKENS = {
    "END": 0x80,
    "FOR": 0x81,
    "NEXT": 0x82,
    "DATA": 0x83,
    "INPUT#": 0x84,
    "INPUT": 0x85,
    "DIM": 0x86,
    "READ": 0x87,
    "LET": 0x88,
    "GOTO": 0x89,
    "RUN": 0x8A,
    "IF": 0x8B,
    "RESTORE": 0x8C,
    "GOSUB": 0x8D,
    "RETURN": 0x8E,
    "REM": 0x8F,
    "STOP": 0x90,
    "ON": 0x91,
    "WAIT": 0x92,
    "LOAD": 0x93,
    "SAVE": 0x94,
    "VERIFY": 0x95,
    "DEF": 0x96,
    "POKE": 0x97,
    "PRINT#": 0x98,
    "PRINT": 0x99,
    "CONT": 0x9A,
    "LIST": 0x9B,
    "CLR": 0x9C,
    "CMD": 0x9D,
    "SYS": 0x9E,
    "OPEN": 0x9F,
    "CLOSE": 0xA0,
    "GET": 0xA1,
    "NEW": 0xA2,
    "TAB(": 0xA3,
    "TO": 0xA4,
    "FN": 0xA5,
    "SPC(": 0xA6,
    "THEN": 0xA7,
    "NOT": 0xA8,
    "STEP": 0xA9,
    "+": 0xAA,
    "-": 0xAB,
    "*": 0xAC,
    "/": 0xAD,
    "^": 0xAE,
    "AND": 0xAF,
    "OR": 0xB0,
    ">": 0xB1,
    "=": 0xB2,
    "<": 0xB3,
    "SGN": 0xB4,
    "INT": 0xB5,
    "ABS": 0xB6,
    "USR": 0xB7,
    "FRE": 0xB8,
    "POS": 0xB9,
    "SQR": 0xBA,
    "RND": 0xBB,
    "LOG": 0xBC,
    "EXP": 0xBD,
    "COS": 0xBE,
    "SIN": 0xBF,
    "TAN": 0xC0,
    "ATN": 0xC1,
    "PEEK": 0xC2,
    "LEN": 0xC3,
    "STR$": 0xC4,
    "VAL": 0xC5,
    "ASC": 0xC6,
    "CHR$": 0xC7,
    "LEFT$": 0xC8,
    "RIGHT$": 0xC9,
    "MID$": 0xCA,
    "GO": 0xCB,
}


MDBASIC_TOKENS = {
    "OFF": 0xCB,
    "ELSE": 0xCC,
    "MERGE": 0xCD,
    "DUMP": 0xCE,
    "VARS": 0xCF,
    "CIRCLE": 0xD0,
    "FILL": 0xD1,
    "SCROLL": 0xD2,
    "SWAP": 0xD3,
    "CURSOR": 0xD4,
    "DISK": 0xD5,
    "DELETE": 0xD6,
    "FILES": 0xD7,
    "COLOR": 0xD8,
    "MOVE": 0xD9,
    "SPRITE": 0xDA,
    "SPRCOL": 0xDB,
    "FIND": 0xDC,
    "SERIAL": 0xDD,
    "DESIGN": 0xDE,
    "TRACE": 0xDF,
    "MAPCOL": 0xE0,
    "PLOT": 0xE1,
    "LINE": 0xE2,
    "PAINT": 0xE3,
    "DRAW": 0xE4,
    "RENUM": 0xE5,
    "TEXT": 0xE6,
    "SCREEN": 0xE7,
    "RESUME": 0xE8,
    "ENVELOPE": 0xE9,
    "WAVE": 0xEA,
    "VOICE": 0xEB,
    "PULSE": 0xEC,
    "VOL": 0xED,
    "FILTER": 0xEE,
    "PLAY": 0xEF,
    "AUTO": 0xF0,
    "OLD": 0xF1,
    "ERR": 0xF2,
    "KEY": 0xF3,
    "TIME": 0xF4,
    "ROUND": 0xF5,
    "TRIM": 0xF6,
    "MOD": 0xF7,
    "PTR": 0xF8,
    "INF": 0xF9,
    "PEN": 0xFA,
    "JOY": 0xFB,
    "POT": 0xFC,
    "HEX$": 0xFD,
    "INSTR": 0xFE,
}


CONTROL_CODES = {
    "RETURN": 0x0D,
    "CLR": 0x93,
    "HOME": 0x13,
    "RVS": 0x12,
    "RVSOFF": 0x92,
    "DOWN": 0x11,
    "UP": 0x91,
    "RIGHT": 0x1D,
    "LEFT": 0x9D,
}


LINE_RE = re.compile(r"^\s*(\d+)\s?(.*)$")


def petscii_bytes(text: str) -> bytes:
    out = bytearray()
    i = 0
    while i < len(text):
        if text[i] == "{" and "}" in text[i:]:
            j = text.index("}", i)
            name = text[i + 1 : j].upper()
            if name not in CONTROL_CODES:
                raise ValueError(f"unknown control code {{{name}}}")
            out.append(CONTROL_CODES[name])
            i = j + 1
            continue
        ch = text[i]
        code = ord(ch)
        if code == 0x0A:
            i += 1
            continue
        if code > 0xFF:
            raise ValueError(f"character {ch!r} is outside PETSCII byte range")
        out.append(code)
        i += 1
    return bytes(out)


def token_table(dialect: str) -> dict[str, int]:
    tokens = dict(BASIC_V2_TOKENS)
    if dialect == "mdbasic":
        tokens.update(MDBASIC_TOKENS)
    return tokens


def tokenize_body(body: str, dialect: str) -> bytes:
    source = body.upper()
    tokens = sorted(token_table(dialect).items(), key=lambda kv: len(kv[0]), reverse=True)
    out = bytearray()
    i = 0
    in_quote = False
    after_rem = False
    while i < len(source):
        ch = source[i]
        if ch == '"':
            in_quote = not in_quote
            out.append(ord(ch))
            i += 1
            continue
        if in_quote or after_rem:
            out.extend(petscii_bytes(source[i]))
            i += 1
            continue
        if ch == "?":
            out.append(BASIC_V2_TOKENS["PRINT"])
            i += 1
            continue
        matched = False
        for word, token in tokens:
            if source.startswith(word, i):
                out.append(token)
                i += len(word)
                matched = True
                if word == "REM":
                    after_rem = True
                break
        if matched:
            continue
        out.extend(petscii_bytes(ch))
        i += 1
    return bytes(out)


def compile_basic(source: str, dialect: str, load_address: int) -> bytes:
    lines: list[tuple[int, bytes]] = []
    for raw_line in source.splitlines():
        if not raw_line.strip():
            continue
        match = LINE_RE.match(raw_line)
        if not match:
            raise ValueError(f"missing BASIC line number: {raw_line!r}")
        number = int(match.group(1))
        if not 0 <= number <= 63999:
            raise ValueError(f"line number out of range: {number}")
        lines.append((number, tokenize_body(match.group(2), dialect)))

    program = bytearray(load_address.to_bytes(2, "little"))
    body_address = load_address
    for number, tokenized in lines:
        next_address = body_address + 5 + len(tokenized)
        program.extend(next_address.to_bytes(2, "little"))
        program.extend(number.to_bytes(2, "little"))
        program.extend(tokenized)
        program.append(0)
        body_address = next_address
    program.extend(b"\x00\x00")
    return bytes(program)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--dialect", choices=("basic2", "mdbasic"), default="basic2")
    parser.add_argument("--load-address", default="0x0801")
    args = parser.parse_args()

    load_address = int(args.load_address, 0)
    prg = compile_basic(args.source.read_text(encoding="utf-8"), args.dialect, load_address)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(prg)


if __name__ == "__main__":
    main()
