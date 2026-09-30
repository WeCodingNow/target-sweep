# target-sweep

Finds cargo target directories under a root, shows them as a checklist with
their size and age, and deletes the ones you pick.

```sh
uv tool install -e ~/Code/target-sweep   # puts `target-sweep` on PATH
target-sweep ~/Code                      # or: uv run target-sweep ~/Code
target-sweep --days 7 --dry-run ~/Code
```

A directory counts as a target dir when cargo has left `.rustc_info.json` or a
cargo `CACHEDIR.TAG` in it. The scan does not descend into a target dir, so a
rust-analyzer target dir kept inside the main one is measured as part of it.

Age is the time since the newest file or directory inside was modified (GNU
`du --time`). A directory is pre-selected when its age exceeds `--days`
(default 3) and it is not pinned.

| Key | Action |
|---|---|
| ↑/↓, j/k, PgUp/PgDn, g/G | move |
| space | toggle |
| p | pin / unpin: a pinned dir is never pre-selected |
| a / n | select all unpinned / none (`a` leaves pinned dirs as they are) |
| s | cycle sort: size (largest first), project (by path, so worktrees of one repo sit together), age (oldest first) |
| enter | delete the selected dirs, after a y/N confirmation |
| q, Esc | quit without deleting |

Pins are saved as soon as they change, in
`$XDG_CONFIG_HOME/target-sweep/pins.json` (`~/.config/target-sweep/pins.json`
by default).
