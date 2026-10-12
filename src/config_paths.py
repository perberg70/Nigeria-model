"""Load the YAML configuration and resolve the paths it names.

Every model script takes ``--config`` explicitly (no default path), and every
value it reads is looked up with :func:`require`, which names the missing
dotted key instead of substituting a fallback. Relative paths in the config are
resolved against the directory holding the config file.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

CONFIG_ROOT_KEY = "_config_root"


class ConfigError(KeyError):
    """A required configuration key is missing or has the wrong type."""

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else "configuration error"


def add_config_argument(parser: argparse.ArgumentParser) -> None:
    """Add the required ``--config`` option shared by every script."""

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to the YAML configuration (e.g. config.yaml at the repository root).",
    )


def load_config(path: Path | str) -> dict[str, Any]:
    """Read a YAML mapping and record its directory as the root for relative paths."""

    config_path = Path(path).expanduser().resolve()
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, MutableMapping):
        raise ConfigError(f"{config_path}: top level must be a mapping")
    set_config_root(config, config_path.parent)
    return dict(config)


def set_config_root(config: MutableMapping[str, Any], root: Path) -> None:
    """Annotate a config mapping with its filesystem root for relative paths."""

    config[CONFIG_ROOT_KEY] = str(root.resolve())


def get_config_root(config: Mapping[str, Any]) -> Path:
    """Return the base directory that relative paths resolve against."""

    value = config.get(CONFIG_ROOT_KEY)
    if not isinstance(value, str):
        raise ConfigError(f"config has no {CONFIG_ROOT_KEY!r}; load it with load_config()")
    return Path(value)


def require(config: Mapping[str, Any], dotted: str) -> Any:
    """Return ``config[a][b]...`` for ``dotted = "a.b..."``, or raise naming the gap."""

    node: Any = config
    walked: list[str] = []
    for part in dotted.split("."):
        walked.append(part)
        if not isinstance(node, Mapping) or part not in node:
            raise ConfigError(f"missing required config key {'.'.join(walked)!r}")
        node = node[part]
    return node


def resolve_path(config: Mapping[str, Any], value: str | Path) -> Path:
    """Resolve a path from the config against the config file's directory."""

    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (get_config_root(config) / path).resolve()


def require_path(config: Mapping[str, Any], dotted: str) -> Path:
    """Shorthand for ``resolve_path(config, require(config, dotted))``."""

    value = require(config, dotted)
    if not isinstance(value, (str, Path)):
        raise ConfigError(f"config key {dotted!r} must be a path string")
    return resolve_path(config, value)
