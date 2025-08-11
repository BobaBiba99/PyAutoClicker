# PyAutoClicker (Windows, Python)

Lightweight, open-source auto clicker with a friendly recorder and global hotkeys.

## ✨ Features
- **Recorder flow:** Press **Start Recording**, then **hold CTRL** and click anywhere to capture points. Release CTRL to finish.
- **Auto-Save prompt** after recording (toggle in Settings).
- **Never overwrites**: saving a sequence always creates a new file if the name exists.
- **Sequence Manager:** browse, load, delete saved sequences.
- **Hotkeys:** single keys (e.g., `X`, `P`, `1`), named keys (`Space`, `Enter`, `Esc`, arrows, etc.), F-keys, and combos (`Ctrl+Alt+S`).  
- **Status Bubble:** draggable floating bubble that shows the current status and the **loaded profile name**.
- **Safety:** configurable Base interval, jitter, CPS cap, and optional double-clicks.
- **Tray icon** with quick actions.

## 🚀 Install
Requires **Python 3** on Windows.

One-liner (change `<you>` to your GitHub username):
```powershell
irm https://raw.githubusercontent.com/GoblinRules/PyAutoClicker/main/install.ps1 | iex
```

This will:
- Download `pyautoclicker.py` (and optional icon) to `%LOCALAPPDATA%\PyAutoClicker`
- Create a **virtual environment** and install `pynput`, `pystray`, `Pillow`
- Create **Start Menu** and **Desktop** shortcuts

## 🧰 Run manually
```powershell
%LOCALAPPDATA%\PyAutoClicker\.venv\Scripts\pythonw.exe %LOCALAPPDATA%\PyAutoClicker\pyautoclicker.py
```

## 🗂 Sequences
- Saved as JSON files in `%LOCALAPPDATA%\PyAutoClicker\sequences` (or the app folder if you run it portable).
- Each sequence stores metadata (Name, Site, Slot, Date, Notes) plus steps.
- Save dialog includes **Inter‑click delay (ms)** and **Repeats** (0 = infinite).

## ⌨️ Hotkeys (default)
- **Start/Stop:** `F6`
- **Pause/Resume:** `F9`
- **Add point (manual):** `F8`
- **Finish recording (manual):** `Ctrl+F8`
You can change these in **Settings → Hotkeys**. Single keys and combos are supported.

## 🫧 Status Bubble
- Drag anywhere on the bubble to move it.
- Shows the loaded profile name above the status.
- Always on top.

## 📦 Dependencies
```
pynput
pystray
Pillow
```

## 📝 Notes
- On some systems, single-letter global hotkeys can conflict with typing – if that happens, pick a combo like `Ctrl+P`.
- If you want a custom icon, place a `assets/clicker.png` in the repo; the app falls back to a simple placeholder otherwise.

## 🔖 License
GPL-3.0 license
