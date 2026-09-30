"""Pinned target directories: never pre-selected for cleaning.

Pins are absolute paths stored in `$XDG_CONFIG_HOME/target-sweep/pins.json`
(`~/.config/...` when the variable is unset). The file holds pins from every
root ever scanned, so a scan rewrites the whole set it loaded.
"""

import json
import os
from pathlib import Path


def _file() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base, "target-sweep", "pins.json")


def load() -> set[Path]:
    try:
        data = json.loads(_file().read_text())
    except FileNotFoundError:
        return set()
    return {Path(p) for p in data["pinned"]}


def save(pinned: set[Path]) -> None:
    f = _file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"pinned": sorted(map(str, pinned))}, indent=2) + "\n")
