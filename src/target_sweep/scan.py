"""Locate cargo target directories under a root and measure them."""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

# Directories that never hold a cargo target dir worth reporting, skipped to
# keep the walk fast.
SKIP = {".git", "node_modules"}


@dataclass
class Cache:
    path: Path
    size: int  # bytes allocated on disk
    mtime: float  # newest mtime of the directory or anything inside it


def find_target_dirs(root: Path) -> list[Path]:
    """Return the outermost cargo target directories under `root`.

    A directory counts as one when cargo has left `.rustc_info.json` in it or
    tagged it with a cargo `CACHEDIR.TAG`. The walk does not descend into a
    target directory, so nested ones (such as rust-analyzer's own target dir
    kept inside the main one) are reported as part of their parent.
    """
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        if ".rustc_info.json" in filenames or (
            "CACHEDIR.TAG" in filenames and _is_cargo_tag(Path(dirpath, "CACHEDIR.TAG"))
        ):
            found.append(Path(dirpath))
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP]
    return found


def _is_cargo_tag(tag: Path) -> bool:
    try:
        return "created by cargo" in tag.read_text(errors="replace")
    except OSError:
        return False


def measure(path: Path) -> Cache:
    """Measure disk usage and the newest mtime of `path` with GNU `du`."""
    proc = subprocess.run(
        ["du", "-s", "-B1", "--time", "--time-style=+%s", str(path)],
        capture_output=True,
        text=True,
    )
    # du exits non-zero on unreadable entries but still prints the total.
    lines = proc.stdout.splitlines()
    if not lines:
        raise RuntimeError(f"du failed on {path}: {proc.stderr.strip()}")
    size, mtime, _ = lines[-1].split("\t", 2)
    return Cache(path, int(size), float(mtime))


def scan(root: Path, on_progress=lambda done, total: None) -> list[Cache]:
    """Find and measure the cargo target directories under `root`."""
    dirs = find_target_dirs(root)
    caches = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for cache in pool.map(measure, dirs):
            caches.append(cache)
            on_progress(len(caches), len(dirs))
    return caches
