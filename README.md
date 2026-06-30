# File Organiser

**Set your rules once and stop sorting files by hand.** File Organiser watches a
folder and automatically files everything into the right place — in real time,
silently, in the background.

Built for Windows. Free. No Python or setup required — just download and run.

---

## Download

**[⬇️ Download the latest release](https://github.com/BuleWu/file-organisation-tool/releases/latest)** — grab `FileOrganiser.exe` and run it. That's it.

> Current release: **v1.0.0**

### First run on Windows

The app isn't code-signed yet, so the first time you run it Windows SmartScreen
may show a **"Windows protected your PC"** dialog. This is expected for new,
unsigned apps and doesn't mean anything is wrong. To continue:

1. Click **More info**.
2. Click **Run anyway**.

You only need to do this once. (Code signing to remove the prompt is planned.)

---

## What it does

Point it at a folder (say, your Downloads), tell it where organised files should
go, and define a few rules. From then on, every file that lands in the watched
folder is sorted into the right category folder automatically — while you keep
working.

## Features

- **Rule-based sorting** — match files by **extension**, **name**, **prefix**, or
  **path**, and combine conditions with **All / Any / None** logic. Each rule sends
  matching files to a category folder you name.
- **Real-time** — files are organised the moment they appear, using a live folder
  watcher (not slow polling).
- **Runs in the background** — minimise to the **system tray**; the app keeps
  organising. Optionally **launch on Windows startup** and run hidden, so it's
  always working without you lifting a finger.
- **Dry-run preview** — see exactly which files would move where, as a folder
  tree, **before** anything is touched.
- **Custom folder icons** — give each category its own icon so folders are
  recognisable at a glance.
- **Sorting inside folders** — optionally order matched files by **date** or
  **name** (ascending/descending), with numbered prefixes.
- **Conflict handling** — when a file with the same name already exists, choose
  **Keep both**, **Skip**, or **Overwrite**. If the app is hidden in the tray, you
  get a quiet notification and decide when you open it.
- **Organise existing files** — one click to sort files already sitting in the
  folder, not just new ones.
- **Statistics & live log** — see how many files moved, total size, per-category
  counts, and a running feed of every operation.
- **Import / Export rules** — save your rule set to a file to share with a team or
  copy to another device.

## Quick start

1. **Run `FileOrganiser.exe`.**
2. **Rules tab** — pick a **Watched folder** and an **Output folder** (they can be
   the same), then add or edit categories and their conditions. Click **Save rules**.
3. **Control tab** — press **Start**. Drop a file into the watched folder and watch
   it get organised.
4. Want to preview first? Click **Simulate (dry run)**. Want to sort what's already
   there? Click **Organise existing files now**.
5. Close the window to send it to the **tray** — it keeps running. Right-click the
   tray icon for **Open** or **Quit**.
6. To have it start with Windows, toggle **Run on Windows startup** on the Control
   tab.

## Where your settings live

- **Your rules** are saved to `…\AppData\Roaming\FileOrganiser\user_rules.yaml`.
- A **log** is kept at `…\AppData\Roaming\FileOrganiser\file-organiser.log`.
- The app ships with sensible defaults (Images, Documents, Spreadsheets, Videos,
  Audio, Archives, …) so it works on first launch.

## Build from source

Requires Python 3.11+ on Windows.

```bash
pip install -r requirements.txt
python -m src.main
```

To build the standalone executable:

```bash
pip install pyinstaller
pyinstaller FileOrganiser.spec
# -> dist/FileOrganiser.exe
```

(Releases are built automatically by GitHub Actions when a `v*` tag is pushed.)

## Roadmap

This is just the start, and it's built with the community. Planned next:

- **Undo / history** of organise operations
- Reorderable rule **priority**
- More condition types

Have an idea or hit a bug? **[Open an issue](https://github.com/BuleWu/file-organisation-tool/issues)** — your feedback shapes what comes next.
