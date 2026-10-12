"""Make the packages under src/ importable during tests without installation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from config_paths import load_config  # noqa: E402


@pytest.fixture(scope="session")
def config():
    """The repository's own config.yaml."""
    return load_config(ROOT / "config.yaml")


def read_text_lf(path: Path) -> str:
    """File text with CRLF normalised to LF (some committed CSVs were stored as LF)."""
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")
