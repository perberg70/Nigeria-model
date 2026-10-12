"""Capture a printed report and write it next to its memo."""

from __future__ import annotations

import io
from collections.abc import Callable
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


def capture(report: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    """Run a report function and return what it printed."""

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        report(*args, **kwargs)
    return buffer.getvalue()


def short_year(year: int) -> str:
    """The short year the report headers print: 2000 -> "00", 2050 -> "50", 2100 -> "100"."""

    return "%02d" % (year % 1000)


def write_report(path: Path, text: str) -> None:
    """Write a report with LF line endings, as the committed reports are stored."""

    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
