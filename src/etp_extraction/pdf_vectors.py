"""Recover filled rectangles and text runs from a PDF page's content stream.

The ETP charts are VECTOR graphics: each stacked-bar segment is a filled
rectangle in the content stream, so values are recovered from rectangle
geometry rather than from any table. Shared by every chart module here.
"""

from __future__ import annotations

import csv
import os
import re
from collections.abc import Iterable, Sequence
from pathlib import Path


class ExtractionError(RuntimeError):
    """A chart could not be read, or failed a validation gate; nothing was written."""


def colour_key(rgb: Sequence[float]) -> tuple[float, ...]:
    """Fill colour rounded to 3 decimals, the key legends and bars are matched on."""
    return tuple(round(v, 3) for v in rgb)


def write_csv_rows(path: Path, rows: Iterable[Sequence[object]]) -> None:
    """Write rows with the csv module's default dialect (CRLF line endings)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(rows)


def write_csv_atomically(path: Path, rows: Iterable[Sequence[object]]) -> None:
    """Stage to ``<path>.tmp`` and promote with os.replace, so a failure never
    leaves a half-written CSV in place of a committed one."""
    tmp = Path(str(path) + ".tmp")
    write_csv_rows(tmp, rows)
    os.replace(tmp, path)


def tokenize(s):
    """Minimal PDF content-stream tokenizer: numbers, names, strings, arrays, operators."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c == "(":  # literal string
            d, j = 1, i + 1
            while j < n and d:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "(":
                    d += 1
                elif s[j] == ")":
                    d -= 1
                j += 1
            out.append(("str", s[i:j]))
            i = j
            continue
        if c == "<" and i + 1 < n and s[i + 1] != "<":  # hex string
            j = s.find(">", i)
            out.append(("str", s[i : j + 1]))
            i = j + 1
            continue
        if c == "[":  # array (may contain strings)
            d, j = 1, i + 1
            while j < n and d:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "(":
                    dd, j = 1, j + 1
                    while j < n and dd:
                        if s[j] == "\\":
                            j += 2
                            continue
                        if s[j] == "(":
                            dd += 1
                        elif s[j] == ")":
                            dd -= 1
                        j += 1
                    continue
                if s[j] == "[":
                    d += 1
                elif s[j] == "]":
                    d -= 1
                j += 1
            out.append(("arr", s[i:j]))
            i = j
            continue
        if c == "/":
            j = i + 1
            while j < n and s[j] not in " \t\r\n/[]()<>":
                j += 1
            out.append(("name", s[i:j]))
            i = j
            continue
        if c in "<>":
            out.append(("op", s[i : i + 2]))
            i += 2
            continue
        j = i
        while j < n and s[j] not in " \t\r\n/[]()<>":
            j += 1
        t = s[i:j] if j > i else s[i]
        i = max(j, i + 1)
        try:
            out.append(("num", float(t)))
        except ValueError:
            out.append(("op", t))
    return out


def parse_page(page):
    """Return (filled_rects, text_runs) in page coordinates.

    filled_rects: (rgb, x, y, w, h) for every `re` closed by a fill operator.
    text_runs:    (text, x, y) using the text-matrix translation.
    """
    tk = tokenize(page.get_contents().get_data().decode("latin-1"))
    ctm, fill, gs = (1, 0, 0, 1, 0, 0), (0, 0, 0), []
    ops, pend, tm = [], [], None
    rects, texts = [], []

    def apply(m, x, y):
        a, b, c, d, e, f = m
        return (a * x + c * y + e, b * x + d * y + f)

    for i, (typ, val) in enumerate(tk):
        if typ == "num":
            ops.append(val)
            continue
        if typ != "op":
            ops = []
            continue
        if val == "q":
            gs.append((ctm, fill))
        elif val == "Q":
            if gs:
                ctm, fill = gs.pop()
        elif val == "cm" and len(ops) >= 6:
            a, b, c, d, e, f = ops[-6:]
            A, B, C, D, E, F = ctm
            ctm = (
                a * A + b * C,
                a * B + b * D,
                c * A + d * C,
                c * B + d * D,
                e * A + f * C + E,
                e * B + f * D + F,
            )
        elif val == "g" and ops:
            fill = (ops[-1],) * 3
        elif val == "rg" and len(ops) >= 3:
            fill = tuple(ops[-3:])
        elif val == "k" and len(ops) >= 4:  # CMYK -> RGB
            cy, mg, yl, k = ops[-4:]
            fill = ((1 - cy) * (1 - k), (1 - mg) * (1 - k), (1 - yl) * (1 - k))
        elif val in ("sc", "scn") and len(ops) >= 3:
            fill = tuple(ops[-3:])
        elif val == "re" and len(ops) >= 4:
            pend = ops[-4:]
        elif val in ("f", "f*", "B", "B*") and pend:
            x, y, w, h = pend
            p0, p1 = apply(ctm, x, y), apply(ctm, x + w, y + h)
            rects.append(
                (fill, min(p0[0], p1[0]), min(p0[1], p1[1]), abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))
            )
            pend = []
        elif val in ("n", "W", "W*", "S"):
            pend = []  # clip/stroke, not a fill
        elif val == "Tm" and len(ops) >= 6:
            tm = tuple(ops[-6:])
        elif val in ("Tj", "TJ") and tm is not None:
            raw = tk[i - 1][1] if i else ""
            txt = "".join(re.findall(r"\(((?:[^()\\]|\\.)*)\)", raw))
            txt = txt.replace("\\(", "(").replace("\\)", ")")
            if txt.strip():
                p = apply(ctm, tm[4], tm[5])
                texts.append((txt, p[0], p[1]))
        ops = []
    return rects, texts
