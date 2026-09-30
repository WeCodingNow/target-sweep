"""Curses checklist for choosing which target directories to delete."""

import curses
import time
from pathlib import Path

from .scan import Cache

HELP = "↑/↓ j/k move · space toggle · p pin (never pre-select) · a all unpinned · n none · s sort · enter clean · q quit"

# Orders the list cycles through with `s`, keyed by the name shown in the header.
SORTS = {
    "size": lambda c: -c.size,
    "project": lambda c: c.path.parts,
    "age": lambda c: c.mtime,  # oldest first
}


def human_size(n: float) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.1f}{unit}" if unit != "B" else f"{n:.0f}B"
        n /= 1024
    return f"{n:.1f}T"


def human_age(mtime: float) -> str:
    s = max(0, time.time() - mtime)
    if s < 3600:
        return f"{s / 60:.0f}m"
    if s < 86400:
        return f"{s / 3600:.0f}h"
    return f"{s / 86400:.0f}d"


def pick(
    caches: list[Cache],
    root: Path,
    selected: set[Path],
    pinned: set[Path],
    cutoff: float,
    on_pin_change,
) -> list[Cache] | None:
    """Let the user edit `selected` and `pinned` in place.

    Returns the caches chosen for deletion, or None when the user quits.
    `on_pin_change` is called with `pinned` after every pin or unpin.
    Unpinning restores the default: selected when older than `cutoff`.
    """
    return curses.wrapper(_loop, caches, root, selected, pinned, cutoff, on_pin_change)


def _loop(scr, caches, root, selected, pinned, cutoff, on_pin_change):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    caches = sorted(caches, key=SORTS["size"])
    sort_names = list(SORTS)
    sort = 0
    cursor = top = 0
    grand_total = sum(c.size for c in caches)

    while True:
        h, w = scr.getmaxyx()
        rows = max(1, h - 3)
        top = min(max(top, cursor - rows + 1), cursor)
        chosen = [c for c in caches if c.path in selected]

        scr.erase()
        _put(scr, 0, w, f"Rust build caches under {root}", curses.A_BOLD)
        _put(
            scr, 1, w,
            f"{len(chosen)} of {len(caches)} selected: "
            f"{human_size(sum(c.size for c in chosen))} of {human_size(grand_total)}"
            f" · sorted by {sort_names[sort]}",
        )
        for row, c in enumerate(caches[top : top + rows]):
            mark = "[x]" if c.path in selected else "[ ]"
            label = c.path.relative_to(root) if c.path != root else Path(".")
            line = f" {mark} {human_size(c.size):>7} {human_age(c.mtime):>5}  {label}"
            attr = 0
            if c.path in pinned:
                line += "  (pinned)"
                attr = curses.color_pair(2)
            elif c.path in selected:
                attr = curses.color_pair(1)
            if top + row == cursor:
                attr |= curses.A_REVERSE
            _put(scr, 2 + row, w, line, attr)
        _put(scr, h - 1, w, HELP, curses.A_DIM)
        scr.refresh()

        key = scr.getch()
        current = caches[cursor]
        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(caches) - 1, cursor + 1)
        elif key == curses.KEY_PPAGE:
            cursor = max(0, cursor - rows)
        elif key == curses.KEY_NPAGE:
            cursor = min(len(caches) - 1, cursor + rows)
        elif key in (curses.KEY_HOME, ord("g")):
            cursor = 0
        elif key in (curses.KEY_END, ord("G")):
            cursor = len(caches) - 1
        elif key == ord(" "):
            selected ^= {current.path}
        elif key == ord("p"):
            if current.path in pinned:
                pinned.discard(current.path)
                if current.mtime < cutoff:
                    selected.add(current.path)
            else:
                pinned.add(current.path)
                selected.discard(current.path)
            on_pin_change(pinned)
        elif key == ord("s"):
            sort = (sort + 1) % len(sort_names)
            caches.sort(key=SORTS[sort_names[sort]])
            cursor = caches.index(current)
        elif key == ord("a"):
            selected.update(c.path for c in caches if c.path not in pinned)
        elif key == ord("n"):
            selected.clear()
        elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            return chosen
        elif key in (ord("q"), 27):  # 27 is Esc
            return None


def _put(scr, y, w, text, attr=0):
    try:
        scr.addnstr(y, 0, text, w - 1, attr)
    except curses.error:
        pass  # writing to the last cell of the screen raises after drawing
