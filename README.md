# Folder Organizer

A modern, portable PySide6 desktop app that tidies a folder in one click by
moving files into category subfolders based on their extension (or moving
directories into a `Folders` subfolder). Everything lives next to the
executable — no installer, no registry pollution (except an optional autostart
entry).

> Windows, macOS, and Linux supported. Tray icon + autostart features are
> fully functional on Windows; the rest of the app works cross-platform.

---

## Features

- **One-click organize** — Preview what will move before committing, then move.
- **Top-level only** — Only the files/folders directly inside the chosen folder
  are touched. Nested content is left alone.
- **Age window** — Only organize files modified within the last *N* hours
  (24h, 7 days, 30 days, or all files).
- **Configurable categories** — Edit the extension → folder mapping in
  **Settings → Categories**. New extensions create their target folder on the
  spot.
- **Never-move list** — Protect specific files/folders by full path *or* by
  name (matches anywhere). Add from the preview's right-click menu or from
  Settings.
- **Conflict handling** — Choose *Rename (add counter)* or *Skip* when a
  destination file already exists.
- **Hidden / system files** — Skipped by default (toggle in Settings).
- **Undo last batch** — Reverses the most recent organize batch using the
  per-item move log.
- **System tray** — Runs in the background. Right-click menu for *Organize
  now*, *Settings*, and *Quit*.
- **Auto-organize on startup** — Optionally run automatically when the app
  launches (throttled to at most once every 12 hours).
- **Start with Windows** — Optional autostart entry (`--minimized` when
  launched at login).
- **Portable** — `settings.json` and `move_log.jsonl` live next to the script
  or `.exe`. Copy the folder and your data moves with it.

---

## Requirements

- **Python 3.10+** (uses `tuple[...]`, `X | None`, `dict[str, ...]` type syntax)
- **PySide6 ≥ 6.5.0**

Install:

```bash
pip install -r requirements.txt