"""Find cargo target directories under a root and delete the chosen ones."""

import argparse
import shutil
import sys
import time
from pathlib import Path

from . import pins
from .scan import scan
from .ui import human_age, human_size, pick


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="target-sweep",
        description="List Rust (cargo) build directories under ROOT and delete the chosen ones.",
    )
    ap.add_argument("root", nargs="?", default=".", type=Path, help="directory to scan (default: .)")
    ap.add_argument(
        "--days", type=float, default=3,
        help="pre-select caches with nothing modified for longer than this many days (default: 3)",
    )
    ap.add_argument("--dry-run", action="store_true", help="show what would be deleted, delete nothing")
    args = ap.parse_args()

    root = args.root.expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"target-sweep: {root} is not a directory")

    print(f"Scanning {root} ...", file=sys.stderr)
    caches = scan(root, lambda done, total: print(f"\rmeasuring {done}/{total}", end="", file=sys.stderr))
    print(file=sys.stderr)
    if not caches:
        print("No Rust build caches found.")
        return

    pinned = pins.load()
    cutoff = time.time() - args.days * 86400
    selected = {c.path for c in caches if c.mtime < cutoff and c.path not in pinned}

    chosen = pick(caches, root, selected, pinned, cutoff, pins.save)
    if not chosen:
        print("Nothing to delete.")
        return

    for c in chosen:
        print(f"  {human_size(c.size):>7} {human_age(c.mtime):>5}  {c.path}")
    total = human_size(sum(c.size for c in chosen))
    if args.dry_run:
        print(f"Would delete {len(chosen)} directories, {total}.")
        return
    if input(f"Delete {len(chosen)} directories, {total}? [y/N] ").strip().lower() != "y":
        print("Aborted.")
        return

    freed = 0
    for c in chosen:
        print(f"deleting {c.path} ...", end="", flush=True)
        try:
            shutil.rmtree(c.path)
        except OSError as e:
            print(f" failed: {e}")
        else:
            freed += c.size
            print(" done")
    print(f"Freed {human_size(freed)}.")
