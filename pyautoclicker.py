#!/usr/bin/env python3
"""
PyAutoClicker — v1.2
- Floating **status bubble** is draggable anywhere and shows the **loaded profile name**.
- **Recorder**: press **Start Recording**, then **hold CTRL** and click to capture points; release CTRL to finish.
- **Save** always creates a new file (no overwrite). Metadata: Name/Site/Slot/Date/Notes + Inter-delay + Repeats.
- **Sequences Manager** in Settings: browse, load, delete, open folder.
- **Hotkeys** accept single keys (X, P, 1), named keys (<space>, <enter>, arrows, etc.), combos (Ctrl+Alt+S), and F-keys.
- **Dry Run (Preview)**: press F7 to show coloured dots where clicks WOULD happen (no real clicks).
- System tray with Start/Pause/Dry Run/Recorder/Settings; optional bubble overlay.

Dependencies: pynput, pystray, Pillow
"""
import os, sys, time, threading, random, json, configparser, platform, re, string
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from pynput import keyboard, mouse
from pynput.keyboard import Key
import pystray
from PIL import Image

# --- Dry-Run Preview (Windows/Tk overlay) ------------------------------------
# Shows coloured dots where clicks WOULD happen (no real clicks are sent).
# Uses tiny transparent Toplevels so it works across multiple monitors.

import tkinter as _tk
import threading as _thr
import time as _time
from dataclasses import dataclass as _dataclass
from typing import Any as _Any, Optional as _Optional, Tuple as _Tuple, List as _List

@_dataclass
class _PreviewStyle:
    dot_size: int = 18                 # diameter in px
    stay_ms: int = 1100                # how long a dot stays visible
    step_delay_ms: _Optional[int] = None  # None -> use sequence meta or 150ms
    show_numbers: bool = True
    palette: _Tuple[str, ...] = ("#ff3b30", "#34c759", "#007aff", "#ffcc00", "#af52de", "#5ac8fa")

def _dry__extract_points(sequence: _Any):
    """Accepts your sequence dict or a list of step dicts; returns (points, inter_delay_ms)."""
    inter = None
    pts: _List[_Tuple[int,int]] = []
    if isinstance(sequence, dict):
        steps = sequence.get("steps", [])
        inter = (sequence.get("meta") or {}).get("inter_delay_ms")
    else:
        steps = sequence
    for s in steps:
        if isinstance(s, dict):
            x, y = int(s.get("x")), int(s.get("y"))
        else:
            x, y = int(s[0]), int(s[1])
        pts.append((x, y))
    return pts, inter

def _dry__ensure_root() -> _tk.Tk:
    r = _tk._default_root
    if r is None:
        r = _tk.Tk()
        r.withdraw()
    return r

def _dry__make_dot(x: int, y: int, color: str, label: _Optional[str], style: _PreviewStyle):
    top = _tk.Toplevel()
    top.overrideredirect(True)
    try:
        top.attributes("-topmost", True)
        top.wm_attributes("-transparentcolor", "magenta")
    except Exception:
        pass
    r = style.dot_size // 2
    geom = f"{style.dot_size}x{style.dot_size}+{max(x - r, 0)}+{max(y - r, 0)}"
    top.geometry(geom)
    c = _tk.Canvas(top, width=style.dot_size, height=style.dot_size, bg="magenta", highlightthickness=0, bd=0)
    c.pack()
    c.create_oval(1, 1, style.dot_size-1, style.dot_size-1, fill=color, outline=color)
    if label:
        c.create_text(style.dot_size//2, style.dot_size//2, text=label, fill="white", font=("Segoe UI", 8, "bold"))
    top.after(style.stay_ms, top.destroy)

def dry_run_preview(sequence: _Any, style: _Optional[_PreviewStyle] = None, repeats: int = 1):
    """Public API: call to preview the current sequence (non-blocking)."""
    pts, inter = _dry__extract_points(sequence)
    if not pts:
        return
    st = style or _PreviewStyle()
    delay = st.step_delay_ms if st.step_delay_ms is not None else (inter if inter is not None else 150)

    def worker():
        _dry__ensure_root()
        for _ in range(max(1, repeats)):
            for i, (x, y) in enumerate(pts, start=1):
                color = st.palette[(i-1) % len(st.palette)]
                label = str(i) if st.show_numbers else None
                _dry__make_dot(x, y, color, label, st)
                _time.sleep(max(0, delay) / 1000.0)
    _thr.Thread(target=worker, daemon=True).start()
# ----------------------------------------------------------------------------- 

IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    try:
        import winsound
    except Exception:
        winsound = None
else:
    winsound = None

APP_NAME = "PyAutoClicker"
APP_VERSION = "1.2"
CONFIG_DIR_NAME = "config"
SEQUENCES_DIR_NAME = "sequences"
ASSETS_DIR_NAME = "assets"
INI_NAME = "PyAutoClicker.ini"
ICON_NAME = "pyautoclicker.ico"
ICON_PNG = "pyautoclicker.png"

def app_dirs():
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    config_dir = os.path.join(base, CONFIG_DIR_NAME)
    sequences_dir = os.path.join(base, SEQUENCES_DIR_NAME)
    assets_dir = os.path.join(base, ASSETS_DIR_NAME)
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(sequences_dir, exist_ok=True)
    os.makedirs(assets_dir, exist_ok=True)
    return base, config_dir, sequences_dir, assets_dir

BASE_DIR, CONFIG_DIR, SEQUENCES_DIR, ASSETS_DIR = app_dirs()
INI_PATH = os.path.join(CONFIG_DIR, INI_NAME)
ICON_PATH = os.path.join(ASSETS_DIR, ICON_NAME)
ICON_PNG_PATH = os.path.join(ASSETS_DIR, ICON_PNG)

# ---------- Hotkey helpers ----------
NAMED_KEYS = {
    "space":"space", "enter":"enter", "return":"enter", "esc":"esc", "escape":"esc", "tab":"tab",
    "up":"up", "down":"down", "left":"left", "right":"right",
    "home":"home", "end":"end",
    "pgup":"page_up", "pageup":"page_up", "prior":"page_up",
    "pgdn":"page_down", "pagedown":"page_down", "next":"page_down",
    "insert":"insert", "ins":"insert",
    "delete":"delete", "del":"delete",
    "backspace":"backspace", "bksp":"backspace",
    "capslock":"caps_lock", "caps_lock":"caps_lock",
    "printscreen":"print_screen", "prtsc":"print_screen",
    "pause":"pause", "scrolllock":"scroll_lock", "scroll_lock":"scroll_lock",
}

MOD_SYNONYMS = {
    "ctrl":"ctrl", "control":"ctrl",
    "alt":"alt",
    "shift":"shift",
    "cmd":"cmd", "win":"cmd", "super":"cmd", "meta":"cmd"
}

def _is_single_printable(k: str) -> bool:
    return len(k) == 1 and k in (string.ascii_letters + string.digits)

def normalize_hotkey(s: str) -> str:
    """Accept 'F6', 'Ctrl+Alt+S', 'space', 'X', 'p', 'up', 'pageup'.
       Returns GlobalHotKeys format.
       Rule: letters/digits are bare ('x'), named keys and modifiers are in angle brackets ('<space>', '<ctrl>').
    """
    if not s: return ""
    parts = [p.strip().lower() for p in re.split(r"[+\-]", s) if p.strip()]
    if not parts: return ""
    *mod_parts, key_part = parts

    # normalize modifiers
    mods = []
    for m in mod_parts:
        m2 = MOD_SYNONYMS.get(m)
        if not m2:
            return ""  # invalid modifier
        mods.append(m2)

    # normalize key
    key = key_part
    m = re.fullmatch(r"f(\d{1,2})", key)
    if m:
        n = int(m.group(1))
        if not (1 <= n <= 24): return ""
        base_token = f"<f{n}>"
    elif key in NAMED_KEYS:
        base_token = f"<{NAMED_KEYS[key]}>"
    elif _is_single_printable(key):
        base_token = key  # bare
    else:
        if key.startswith("<") and key.endswith(">"):
            base_token = key  # passthrough
        else:
            return ""

    tokens = [f"<{m}>" for m in mods] + [base_token]
    return "+".join(tokens)

def humanize_hotkey(h: str) -> str:
    if not h: return ""
    tokens = h.split("+")
    out = []
    for t in tokens:
        if t.startswith("<") and t.endswith(">"):
            name = t[1:-1].replace("_"," ").title()
            out.append(name if len(name)>1 else name.upper())
        else:
            out.append(t.upper())
    return "+".join(out)

# ---------- Data ----------
@dataclass
class Step:
    x: int
    y: int
    delay_ms: int = 0
    button: str = "left"

@dataclass
class SequenceMeta:
    name: str = ""
    site: str = ""
    slot: str = ""
    date: str = ""
    notes: str = ""
    inter_delay_ms: int = 0
    repeats: int = 0

@dataclass
class Settings:
    # Click behavior
    base_interval_ms: int = 100
    random_ms: int = 0
    jitter_px: int = 0
    max_cps: int = 25
    double_click: int = 0

    # Hotkeys
    hk_start_stop: str = "<f6>"
    hk_pause: str = "<f9>"
    hk_add: str = "<f8>"
    hk_finish: str = "<ctrl>+<f8>"
    hk_dryrun: str = "<f7>"

    # Dry run settings
    dryrun_dot_size: int = 18
    dryrun_stay_ms: int = 1100
    dryrun_show_numbers: int = 1
    dryrun_step_delay_ms: int = -1  # -1 = use sequence meta or 150ms

    # UI
    start_minimized: int = 0
    dark_mode: int = 0
    sounds: int = 1
    hotkeys_enabled: int = 1
    show_bubble: int = 1
    auto_save_after_record: int = 1

    # Sequence state
    current_seq: List[Step] = field(default_factory=list)
    current_meta: SequenceMeta = field(default_factory=SequenceMeta)

    def clamp(self):
        self.base_interval_ms = max(1, int(self.base_interval_ms))
        self.random_ms = max(0, int(self.random_ms))
        self.jitter_px = max(0, int(self.jitter_px))
        self.max_cps = max(1, int(self.max_cps))
        self.double_click = 1 if int(self.double_click) else 0
        # normalize hotkeys (falls back to defaults if invalid)
        self.hk_start_stop = normalize_hotkey(self.hk_start_stop) or "<f6>"
        self.hk_pause      = normalize_hotkey(self.hk_pause) or "<f9>"
        self.hk_add        = normalize_hotkey(self.hk_add) or "<f8>"
        self.hk_finish     = normalize_hotkey(self.hk_finish) or "<ctrl>+<f8>"
        self.hk_dryrun     = normalize_hotkey(getattr(self, "hk_dryrun", "<f7>")) or "<f7>"
        # normalize toggles / ints
        self.start_minimized = 1 if int(self.start_minimized) else 0
        self.dark_mode       = 1 if int(self.dark_mode) else 0
        self.sounds          = 1 if int(self.sounds) else 0
        self.hotkeys_enabled = 1 if int(self.hotkeys_enabled) else 0
        self.show_bubble     = 1 if int(self.show_bubble) else 0
        self.auto_save_after_record = 1 if int(self.auto_save_after_record) else 0
        self.dryrun_show_numbers    = 1 if int(self.dryrun_show_numbers) else 0
        try:
            self.dryrun_step_delay_ms = int(self.dryrun_step_delay_ms)
        except Exception:
            self.dryrun_step_delay_ms = -1

# ---------- utils ----------
def slugify(name: str) -> str:
    name = name.strip()
    if not name: return time.strftime("sequence_%Y%m%d_%H%M%S")
    name = re.sub(r'[<>:"/\\|?*\n\r\t]', "_", name)
    return name

def unique_path(dirpath: str, base_name: str) -> str:
    base = slugify(base_name)
    path = os.path.join(dirpath, base + ".json")
    if not os.path.exists(path):
        return path
    i = 2
    while True:
        path = os.path.join(dirpath, f"{base} ({i}).json")
        if not os.path.exists(path):
            return path
        i += 1

def ellipsis(s: str, maxlen: int = 24) -> str:
    s = s or ""
    return s if len(s) <= maxlen else s[:maxlen-1] + "…"

# ---------- App ----------
class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.s = Settings()
        self.running = False
        self.paused = False
        self.listener = None
        self.mouse = mouse.Controller()
        self.stop_event = threading.Event()
        self.click_thread: Optional[threading.Thread] = None
        self.tray_icon = None

        # recording capture
        self.rec_mouse_listener = None
        self.rec_kb_listener = None
        self.rec_hold_active = False
        self.rec_in_progress = False

        # UI windows
        self.win_settings = None
        self.win_rec = None
        self.win_bubble = None
        self.tree = None

        self.load_settings()
        self.setup_root()
        self.make_tray()
        self.start_hotkeys()

        if not self.s.start_minimized:
            self.root.after(200, self.show_recorder_window)

        if self.s.show_bubble:
            self.root.after(300, self.show_bubble)

    # ----- config -----
    def load_settings(self):
        cfg = configparser.ConfigParser()
        if os.path.exists(INI_PATH):
            cfg.read(INI_PATH, encoding="utf-8")
        if "General" in cfg:
            g = cfg["General"]
            for k in self.s.__dict__.keys():
                if k in ("current_seq","current_meta"): continue
                if k in g:
                    val = g.get(k)
                    if isinstance(getattr(self.s, k), int):
                        try: setattr(self.s, k, int(val))
                        except: pass
                    else:
                        setattr(self.s, k, val)
        self.s.clamp()
        # last sequence snapshot (non-destructive)
        lastp = os.path.join(SEQUENCES_DIR, "_last_sequence.json")
        if os.path.exists(lastp):
            try:
                with open(lastp,"r",encoding="utf-8") as f:
                    data = json.load(f)
                self.s.current_meta = SequenceMeta(**data.get("meta", {}))
                self.s.current_seq = [Step(**st) for st in data.get("steps", [])]
            except Exception:
                pass
        self.save_settings()

    def save_settings(self):
        cfg = configparser.ConfigParser()
        cfg["General"] = {k: str(v) for k,v in self.s.__dict__.items() if k not in ("current_seq","current_meta")}
        with open(INI_PATH,"w",encoding="utf-8") as f:
            cfg.write(f)

    # ----- theme -----
    def setup_root(self):
        self.root.withdraw()
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        try:
            if IS_WINDOWS and os.path.exists(ICON_PATH):
                self.root.iconbitmap(ICON_PATH)
        except Exception: pass
        self.apply_theme()

    def apply_theme(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        if self.s.dark_mode:
            self.root.configure(bg="#1e1f22")
            style.configure(".", background="#1e1f22", foreground="#e6e6e6", fieldbackground="#333")
            style.configure("Treeview", background="#2a2b2f", fieldbackground="#2a2b2f", foreground="#e6e6e6")
        else:
            self.root.configure(bg="#f0f0f0")

    # ----- sounds -----
    def beep(self, f=900, d=70):
        if self.s.sounds and winsound:
            try: winsound.Beep(f,d)
            except Exception: pass

    # ----- tray -----
    def make_tray(self):
        img = Image.open(ICON_PNG_PATH) if os.path.exists(ICON_PNG_PATH) else Image.new("RGBA",(64,64),(90,140,255,255))
        def startstop_text(_): return f"{'Stop' if self.running else 'Start'} ({humanize_hotkey(self.s.hk_start_stop)})"
        menu = pystray.Menu(
            pystray.MenuItem(startstop_text, lambda: self.root.after(0, self.toggle_start_stop)),
            pystray.MenuItem(lambda _: f"{'Resume' if self.paused else 'Pause'} ({humanize_hotkey(self.s.hk_pause)})", lambda: self.root.after(0, self.toggle_pause)),
            pystray.MenuItem("Dry Run (preview)", lambda: self.root.after(0, self._hotkey_dry_run)),
            pystray.MenuItem("Recorder…", lambda: self.root.after(0, self.show_recorder_window)),
            pystray.MenuItem("Settings…", lambda: self.root.after(0, self.show_settings_window)),
            pystray.MenuItem("Exit", lambda: self.root.after(0, self.exit_app))
        )
        self.tray_icon = pystray.Icon("pyautoclicker", img, self.tray_title(), menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def tray_title(self):
        mode = "PAUSED" if self.paused else ("RUNNING" if self.running else "Idle")
        return f"{APP_NAME} {APP_VERSION} — {mode}"

    def update_tray(self):
        if self.tray_icon:
            self.tray_icon.title = self.tray_title()

    # ----- hotkeys -----
    def start_hotkeys(self):
        if hasattr(self, "listener") and self.listener:
            try: self.listener.stop()
            except Exception: pass
        if not self.s.hotkeys_enabled: return
        combos = {
            self.s.hk_start_stop: lambda: self.root.after(0, self.toggle_start_stop),
            self.s.hk_pause:      lambda: self.root.after(0, self.toggle_pause),
            self.s.hk_add:        lambda: self.root.after(0, self.add_point_manual),
            self.s.hk_finish:     lambda: self.root.after(0, self.finish_recording_manual),
            self.s.hk_dryrun:     lambda: self.root.after(0, self._hotkey_dry_run),
            "<ctrl>+<esc>":       lambda: self.root.after(0, self.exit_app),
        }
        self.listener = keyboard.GlobalHotKeys(combos); self.listener.start()

    def restart_hotkeys(self): self.start_hotkeys()

    # ----- click helpers -----
    def human_delay(self, base_ms:int)->float:
        r = self.s.random_ms
        if r>0: base_ms += random.randint(-r,r)
        base_ms = max(base_ms, int(1000/self.s.max_cps))
        return max(0, base_ms)/1000.0

    def apply_jitter(self,x:int,y:int)->Tuple[int,int]:
        j=self.s.jitter_px
        if j>0: x+=random.randint(-j,j); y+=random.randint(-j,j)
        return x,y

    def do_click(self, btn_name:str, x:int, y:int):
        btn_map={"left":mouse.Button.left,"right":mouse.Button.right,"middle":mouse.Button.middle}
        btn=btn_map.get(btn_name, mouse.Button.left)
        x,y=self.apply_jitter(x,y)
        self.mouse.position=(x,y)
        self.mouse.click(btn, 2 if self.s.double_click else 1)

    # ----- worker -----
    def click_worker(self):
        try:
            meta = self.s.current_meta
            inter = int(meta.inter_delay_ms) if meta and meta.inter_delay_ms>0 else None
            repeats = int(meta.repeats) if meta and meta.repeats>0 else None
            def wait_ms(ms): time.sleep(self.human_delay(ms))
            if not self.s.current_seq:
                while not self.stop_event.is_set():
                    if self.paused: time.sleep(0.05); continue
                    x,y=self.mouse.position
                    self.do_click("left",x,y)
                    wait_ms(self.s.base_interval_ms)
            else:
                passes_done=0
                while not self.stop_event.is_set():
                    for st in self.s.current_seq:
                        if self.stop_event.is_set(): break
                        while self.paused and not self.stop_event.is_set():
                            time.sleep(0.05)
                        delay = inter if inter is not None else st.delay_ms
                        wait_ms(delay)
                        self.do_click(st.button, st.x, st.y)
                    passes_done+=1
                    if repeats is not None and passes_done>=repeats:
                        break
        finally:
            self.running=False
            self.root.after(0, self.update_tray)

    # ----- start/stop/pause -----
    def toggle_start_stop(self):
        if self.running:
            self.stop_event.set()
            if self.click_thread and self.click_thread.is_alive():
                self.click_thread.join(timeout=1.5)
            self.running=False; self.paused=False
            self.update_tray(); self.beep(600,70)
        else:
            self.stop_event.clear(); self.paused=False; self.running=True
            self.click_thread=threading.Thread(target=self.click_worker, daemon=True); self.click_thread.start()
            self.update_tray(); self.beep(1000,70)

    def toggle_pause(self):
        if not self.running: return
        self.paused = not self.paused
        self.update_tray(); self.beep(750 if self.paused else 900,70)

    # ----- Dry Run (Preview) -----
    def _hotkey_dry_run(self):
        # Build sequence from current state (loaded or in-memory); preview without clicking
        try:
            meta_delay = None
            if getattr(self.s, "current_meta", None):
                meta_delay = int(getattr(self.s.current_meta, "inter_delay_ms", 0)) or None
        except Exception:
            meta_delay = None
        seq = {
            "meta": {"inter_delay_ms": meta_delay if meta_delay is not None else 150},
            "steps": [{"x": int(st.x), "y": int(st.y)} for st in (self.s.current_seq or [])]
        }
        if not seq["steps"]:
            try:
                x, y = self.mouse.position
                seq["steps"] = [{"x": int(x), "y": int(y)}]
            except Exception:
                pass
        st = _PreviewStyle(
            dot_size=max(6, int(getattr(self.s, "dryrun_dot_size", 18))),
            stay_ms=max(200, int(getattr(self.s, "dryrun_stay_ms", 1100))),
            show_numbers=bool(int(getattr(self.s, "dryrun_show_numbers", 1))),
            step_delay_ms=(None if int(getattr(self.s, "dryrun_step_delay_ms", -1)) < 0
                           else int(getattr(self.s, "dryrun_step_delay_ms", 150)))
        )
        dry_run_preview(seq, st, repeats=1)

    # ----- Recorder (hold CTRL to capture clicks) -----
    def show_recorder_window(self):
        if self.win_rec and self.win_rec.winfo_exists():
            self.win_rec.deiconify(); self.win_rec.lift(); return

        w = tk.Toplevel(self.root); self.win_rec = w
        w.title(f"Recorder — {APP_NAME} {APP_VERSION}")
        w.resizable(False, False)

        top = ttk.Frame(w, padding=8); top.grid(row=0, column=0, sticky="nsew")
        ttk.Button(top, text="Start Recording (hold Ctrl & click)", command=self.start_recording).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(top, text="Finish", command=self.finish_recording_manual).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(top, text="Clear", command=self.clear_sequence).grid(row=0, column=2, padx=4, pady=4)

        ttk.Label(top, text="Tip: Hold CTRL and click to capture points. Release CTRL to stop.").grid(row=1, column=0, columnspan=3, sticky="w")

        cols=("idx","x","y","btn")
        tree=ttk.Treeview(w, columns=cols, show="headings", height=10)
        for c,h,wd in zip(cols,["#","X","Y","Button"],[40,100,100,100]):
            tree.heading(c,text=h); tree.column(c,width=wd, anchor="center")
        tree.grid(row=1,column=0,sticky="nsew", padx=8, pady=6)
        self.tree=tree

        row2 = ttk.Frame(w, padding=8); row2.grid(row=2,column=0,sticky="ew")
        ttk.Button(row2, text="Up", command=lambda:self._tree_move(-1)).pack(side="left", padx=4)
        ttk.Button(row2, text="Down", command=lambda:self._tree_move(1)).pack(side="left", padx=4)
        ttk.Button(row2, text="Delete", command=self._tree_delete).pack(side="left", padx=4)
        ttk.Button(row2, text="Save Sequence…", command=self.save_sequence_dialog).pack(side="right", padx=4)
        ttk.Button(row2, text="Load Sequence…", command=self.load_sequence_dialog).pack(side="right", padx=4)

        self.refresh_tree()
        w.protocol("WM_DELETE_WINDOW", w.withdraw)

    def _tree_selected_index(self) -> Optional[int]:
        if not self.tree: return None
        sel = self.tree.focus()
        if not sel: return None
        try:
            vals = self.tree.item(sel, "values")
            return int(vals[0]) - 1  # first column is 1-based index
        except Exception:
            return None

    def _tree_move(self, delta: int):
        idx = self._tree_selected_index()
        if idx is None: return
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self.s.current_seq): return
        self.s.current_seq[idx], self.s.current_seq[new_idx] = self.s.current_seq[new_idx], self.s.current_seq[idx]
        self.refresh_tree()
        # reselect moved row
        for iid in self.tree.get_children():
            vals = self.tree.item(iid, "values")
            if int(vals[0]) == new_idx+1:
                self.tree.selection_set(iid); self.tree.focus(iid); break

    def _tree_delete(self):
        idx = self._tree_selected_index()
        if idx is None: return
        del self.s.current_seq[idx]
        self.refresh_tree()

    def start_recording(self):
        if self.rec_in_progress: return
        self.s.current_seq = []
        self.s.current_meta = SequenceMeta()
        self.rec_in_progress = True
        self.rec_hold_active = False
        self.beep(1200,70)
        self.rec_mouse_listener = mouse.Listener(on_click=self._rec_on_click)
        self.rec_kb_listener = keyboard.Listener(on_press=self._rec_on_press, on_release=self._rec_on_release)
        self.rec_mouse_listener.start(); self.rec_kb_listener.start()
        self.tip("Recording: hold CTRL and click to capture points.")

    def finish_recording_manual(self):
        self._stop_rec_listeners()
        if not self.rec_in_progress:
            return
        self.rec_in_progress=False
        self.rec_hold_active=False
        self.beep(1000,70)
        self.tip(f"Recording finished. {len(self.s.current_seq)} step(s).")
        self.refresh_tree()
        if self.s.current_seq:
            self._save_last_snapshot()
            if self.s.auto_save_after_record:
                self.root.after(0, self.save_sequence_dialog)

    def _stop_rec_listeners(self):
        try:
            if self.rec_mouse_listener: self.rec_mouse_listener.stop()
        except Exception: pass
        try:
            if self.rec_kb_listener: self.rec_kb_listener.stop()
        except Exception: pass
        self.rec_mouse_listener=None; self.rec_kb_listener=None

    def _rec_on_press(self, key):
        if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r): self.rec_hold_active=True

    def _rec_on_release(self, key):
        if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
            self.rec_hold_active=False
            self.root.after(0, self.finish_recording_manual)

    def _rec_on_click(self, x, y, button, pressed):
        if not pressed: return
        if self.rec_in_progress and self.rec_hold_active:
            btn_name = "left" if button == mouse.Button.left else "right" if button == mouse.Button.right else "middle"
            self.s.current_seq.append(Step(x=int(x), y=int(y), delay_ms=0, button=btn_name))
            self.root.after(0, self.refresh_tree)

    def add_point_manual(self):
        x, y = self.mouse.position
        self.s.current_seq.append(Step(x=int(x), y=int(y), delay_ms=0, button="left"))
        self.refresh_tree()

    def clear_sequence(self):
        self.s.current_seq.clear()
        self.refresh_tree()

    def _save_last_snapshot(self):
        path = os.path.join(SEQUENCES_DIR, "_last_sequence.json")
        payload = {"meta": asdict(self.s.current_meta), "steps":[asdict(s) for s in self.s.current_seq]}
        try:
            with open(path,"w",encoding="utf-8") as f: json.dump(payload,f,indent=2)
        except Exception: pass

    def refresh_tree(self):
        if not self.tree: return
        self.tree.delete(*self.tree.get_children())
        for i, st in enumerate(self.s.current_seq, start=1):
            self.tree.insert("", "end", values=(i, st.x, st.y, st.button))

    # Save/Load with metadata, inter-delay, repeats
    def save_sequence_dialog(self):
        meta = self._sequence_meta_dialog()
        if not meta: return
        self.s.current_meta = meta
        payload = {"meta": asdict(meta), "steps":[asdict(s) for s in self.s.current_seq]}
        path = unique_path(SEQUENCES_DIR, meta.name or time.strftime("sequence_%Y%m%d_%H%M%S"))
        with open(path,"w",encoding="utf-8") as f: json.dump(payload,f,indent=2)
        self.tip(f"Saved sequence '{os.path.basename(path)}'.")
        self._save_last_snapshot()

    def load_sequence_dialog(self):
        p = filedialog.askopenfilename(initialdir=SEQUENCES_DIR, filetypes=[("Sequences","*.json")])
        if not p: return
        with open(p,"r",encoding="utf-8") as f: data=json.load(f)
        self.s.current_meta = SequenceMeta(**data.get("meta",{}))
        self.s.current_seq = [Step(**st) for st in data.get("steps",[])]
        self.refresh_tree()

    def _sequence_meta_dialog(self)->Optional[SequenceMeta]:
        d = tk.Toplevel(self.root); d.title("Save Sequence — Details"); d.resizable(False, False)
        labels = [("Name","name"),("Site","site"),("Slot","slot"),("Date","date"),("Notes","notes"),("Inter-click delay (ms)","inter_delay_ms"),("Repeats (1–100000, 0=∞)","repeats")]
        vars = {key: tk.StringVar() for _,key in labels}
        vars["inter_delay_ms"].set("100")
        vars["repeats"].set("0")
        for i,(lbl,key) in enumerate(labels):
            ttk.Label(d, text=lbl+":").grid(row=i, column=0, sticky="e", padx=6, pady=4)
            ttk.Entry(d, textvariable=vars[key], width=32).grid(row=i, column=1, sticky="w", padx=6, pady=4)
        out=None
        def ok():
            nonlocal out
            try:
                delay = max(0, int(vars["inter_delay_ms"].get() or "0"))
                reps = int(vars["repeats"].get() or "0")
                if reps<0 or reps>100000: raise ValueError("Repeats out of range")
            except Exception:
                messagebox.showerror("Invalid values", "Please enter a valid delay and repeat count (0 or 1–100000)."); return
            out = SequenceMeta(
                name=vars["name"].get().strip(),
                site=vars["site"].get().strip(),
                slot=vars["slot"].get().strip(),
                date=vars["date"].get().strip(),
                notes=vars["notes"].get().strip(),
                inter_delay_ms=delay,
                repeats=reps
            )
            d.destroy()
        ttk.Button(d, text="Save", command=ok).grid(row=len(labels), column=0, columnspan=2, pady=8)
        d.wait_window()
        return out

    # ----- Settings window with tabs (General/Hotkeys/Preview/Sequences/Help) -----
    def show_settings_window(self):
        if self.win_settings and self.win_settings.winfo_exists():
            self.win_settings.deiconify(); self.win_settings.lift(); return

        w = tk.Toplevel(self.root); self.win_settings = w
        w.title(f"Settings — {APP_NAME} {APP_VERSION}")
        w.resizable(False, False)
        nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True)

        # General tab
        tab1 = ttk.Frame(nb, padding=10); nb.add(tab1, text="General")
        row=0
        ttk.Label(tab1, text="Base interval (ms):").grid(row=row,column=0,sticky="w"); v_bi=tk.StringVar(value=str(self.s.base_interval_ms)); ttk.Entry(tab1, textvariable=v_bi, width=10).grid(row=row,column=1,sticky="w"); row+=1
        ttk.Label(tab1, text="Used only when no sequence is recorded — clicks at current cursor.").grid(row=row,column=0,columnspan=2,sticky="w"); row+=1
        ttk.Label(tab1, text="Random time jitter (±ms):").grid(row=row,column=0,sticky="w"); v_rm=tk.StringVar(value=str(self.s.random_ms)); ttk.Entry(tab1, textvariable=v_rm, width=10).grid(row=row,column=1,sticky="w"); row+=1
        ttk.Label(tab1, text="Pixel jitter (±px):").grid(row=row,column=0,sticky="w"); v_jp=tk.StringVar(value=str(self.s.jitter_px)); ttk.Entry(tab1, textvariable=v_jp, width=10).grid(row=row,column=1,sticky="w"); row+=1
        ttk.Label(tab1, text="Max CPS (safety cap):").grid(row=row,column=0,sticky="w"); v_cps=tk.StringVar(value=str(self.s.max_cps)); ttk.Entry(tab1, textvariable=v_cps, width=10).grid(row=row,column=1,sticky="w"); row+=1
        v_dc=tk.IntVar(value=self.s.double_click); ttk.Checkbutton(tab1, text="Double-click each step", variable=v_dc).grid(row=row,column=0,columnspan=2,sticky="w"); row+=1
        v_dark=tk.IntVar(value=self.s.dark_mode); ttk.Checkbutton(tab1, text="Dark mode", variable=v_dark).grid(row=row,column=0,columnspan=2,sticky="w"); row+=1
        v_auto=tk.IntVar(value=self.s.auto_save_after_record); ttk.Checkbutton(tab1, text="Auto-open 'Save Sequence' after recording", variable=v_auto).grid(row=row,column=0,columnspan=2,sticky="w"); row+=1
        ttk.Button(tab1, text="Open Recorder…", command=self.show_recorder_window).grid(row=row,column=0, pady=(6,8)); row+=1
        ttk.Button(tab1, text="Save", command=lambda:self._save_general(v_bi,v_rm,v_jp,v_cps,v_dc,v_dark,v_auto)).grid(row=row,column=0,pady=8)

        # Hotkeys tab
        tab2 = ttk.Frame(nb, padding=10); nb.add(tab2, text="Hotkeys")
        row=0
        def hkrow(lbl, val):
            nonlocal row
            ttk.Label(tab2, text=lbl).grid(row=row,column=0,sticky="w")
            sv=tk.StringVar(value=humanize_hotkey(val))
            ttk.Entry(tab2, textvariable=sv, width=18).grid(row=row,column=1,sticky="w"); row+=1
            return sv
        hk_start=hkrow("Start/Stop:", self.s.hk_start_stop)
        hk_pause=hkrow("Pause/Resume:", self.s.hk_pause)
        hk_add=hkrow("Add point (manual):", self.s.hk_add)
        hk_finish=hkrow("Finish recording (manual):", self.s.hk_finish)
        row += 1
        hk_dry=hkrow("Dry Run (preview):", self.s.hk_dryrun)
        ttk.Button(tab2, text="Save", command=lambda:self._save_hotkeys(hk_start,hk_pause,hk_add,hk_finish,hk_dry)).grid(row=row,column=0,pady=8)

        # Preview tab (for dot style)
        tabP = ttk.Frame(nb, padding=10); nb.add(tabP, text="Preview")
        ttk.Label(tabP, text="Dry Run (Preview) settings").grid(row=0,column=0,columnspan=2,sticky="w",pady=(0,6))
        v_psize = tk.StringVar(value=str(getattr(self.s, "dryrun_dot_size", 18)))
        v_pstay = tk.StringVar(value=str(getattr(self.s, "dryrun_stay_ms", 1100)))
        v_pnum  = tk.IntVar(value=int(getattr(self.s, "dryrun_show_numbers", 1)))
        v_pstep = tk.StringVar(value=str(getattr(self.s, "dryrun_step_delay_ms", -1)))
        ttk.Label(tabP, text="Dot size (px):").grid(row=1,column=0,sticky="w"); ttk.Entry(tabP,textvariable=v_psize,width=8).grid(row=1,column=1,sticky="w")
        ttk.Label(tabP, text="Dot stay (ms):").grid(row=2,column=0,sticky="w"); ttk.Entry(tabP,textvariable=v_pstay,width=8).grid(row=2,column=1,sticky="w")
        ttk.Checkbutton(tabP, text="Show step numbers", variable=v_pnum).grid(row=3,column=0,columnspan=2,sticky="w")
        ttk.Label(tabP, text="Step delay override (ms):").grid(row=4,column=0,sticky="w")
        ttk.Entry(tabP,textvariable=v_pstep,width=8).grid(row=4,column=1,sticky="w")
        ttk.Label(tabP, text="Use -1 to use the sequence's inter-delay; otherwise this value is used.").grid(row=5,column=0,columnspan=2,sticky="w")
        def save_prev():
            try:
                self.s.dryrun_dot_size=max(6,int(v_psize.get() or 18))
                self.s.dryrun_stay_ms=max(200,int(v_pstay.get() or 1100))
                self.s.dryrun_show_numbers=1 if int(v_pnum.get()) else 0
                self.s.dryrun_step_delay_ms=int(v_pstep.get() or -1)
                self.s.clamp(); self.save_settings(); self.tip("Preview settings saved.")
            except Exception as e:
                messagebox.showerror("Invalid values", str(e))
        ttk.Button(tabP, text="Save", command=save_prev).grid(row=6,column=0,pady=10)

        # Sequences tab (manager)
        tab4 = ttk.Frame(nb, padding=10); nb.add(tab4, text="Sequences")
        self._build_sequence_manager(tab4)

        # Help tab
        tab5 = ttk.Frame(nb, padding=10); nb.add(tab5, text="Help")
        help_txt = (
            f"{APP_NAME} {APP_VERSION}\n\n"
            "Hotkeys:\n"
            " • Single keys like X, P, 1 (bare keys) or named keys: Space, Enter, Esc, Tab, arrows, Home/End, PageUp/Down, Insert, Delete, Backspace.\n"
            " • Combos like Ctrl+Alt+S, and F-keys like F6.\n"
            " • Dry Run: press F7 to preview coloured dots where clicks would happen (no real clicks).\n\n"
            "Recorder:\n"
            " • Click 'Start Recording', then hold CTRL and click to add points. Release CTRL to stop.\n"
            " • When saving, set Inter-click delay (ms) and Repeat count (0 = infinite).\n"
            " • Save never overwrites; it creates a new file automatically.\n\n"
            "Playback:\n"
            " • Start/Stop, Pause/Resume via hotkeys or tray/bubble.\n"
            " • If a sequence is loaded and you set Inter-delay/Repeats in its metadata, those override per-step delays.\n\n"
            "Bubble:\n"
            " • Drag anywhere on the bubble to move it; it shows the loaded sequence name.\n"
        )
        txt = tk.Text(tab5, width=70, height=18, wrap="word")
        txt.insert("1.0", help_txt)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True)

        w.protocol("WM_DELETE_WINDOW", w.withdraw)

    def _build_sequence_manager(self, parent):
        cols = ("name","site","slot","date","notes","delay","repeats","steps","file")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=10)
        headings = ["Name","Site","Slot","Date","Notes","Delay(ms)","Repeats","Count","File"]
        widths   = [160,120,120,110,240,90,80,60,180]
        for c, h, wd in zip(cols, headings, widths):
            tree.heading(c, text=h); tree.column(c, width=wd, anchor="center")
        tree.pack(fill="both", expand=True, pady=(0,8))

        def refresh():
            tree.delete(*tree.get_children())
            for fn in sorted(os.listdir(SEQUENCES_DIR)):
                if not fn.lower().endswith(".json"): continue
                try:
                    with open(os.path.join(SEQUENCES_DIR, fn), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    meta = data.get("meta", {})
                    steps = data.get("steps", [])
                    tree.insert("", "end", iid=fn, values=(
                        meta.get("name",""), meta.get("site",""), meta.get("slot",""),
                        meta.get("date",""), meta.get("notes",""),
                        meta.get("inter_delay_ms",0), meta.get("repeats",0), len(steps), fn
                    ))
                except Exception:
                    pass
        refresh()

        btns = ttk.Frame(parent); btns.pack(fill="x")
        def load_sel():
            sel = tree.focus()
            if not sel: return
            path = os.path.join(SEQUENCES_DIR, sel)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.s.current_meta = SequenceMeta(**data.get("meta", {}))
            self.s.current_seq = [Step(**s) for s in data.get("steps", [])]
            self.refresh_tree()
            self.tip(f"Loaded '{sel}'.")
        def del_sel():
            sel = tree.focus()
            if not sel: return
            path = os.path.join(SEQUENCES_DIR, sel)
            try:
                os.remove(path); refresh(); self.tip(f"Deleted '{sel}'.")
            except Exception as e:
                messagebox.showerror("Delete failed", str(e))
        def open_folder():
            folder = os.path.realpath(SEQUENCES_DIR)
            if IS_WINDOWS:
                os.startfile(folder)
            else:
                import subprocess, platform as _pf
                subprocess.Popen(["open" if _pf.system()=="Darwin" else "xdg-open", folder])
        ttk.Button(btns, text="Load selected", command=load_sel).pack(side="left", padx=4, pady=4)
        ttk.Button(btns, text="Delete selected", command=del_sel).pack(side="left", padx=4, pady=4)
        ttk.Button(btns, text="Refresh", command=refresh).pack(side="left", padx=4, pady=4)
        ttk.Button(btns, text="Open folder", command=open_folder).pack(side="right", padx=4, pady=4)

    # ----- Settings save helpers -----
    def _save_general(self, v_bi,v_rm,v_jp,v_cps,v_dc,v_dark,v_auto):
        self.s.base_interval_ms=int(v_bi.get() or 100)
        self.s.random_ms=int(v_rm.get() or 0)
        self.s.jitter_px=int(v_jp.get() or 0)
        self.s.max_cps=int(v_cps.get() or 25)
        self.s.double_click=int(v_dc.get() or 0)
        self.s.dark_mode=int(v_dark.get() or 0)
        self.s.auto_save_after_record=int(v_auto.get() or 1)
        self.s.clamp(); self.save_settings(); self.apply_theme(); self.tip("General saved.")

    def _save_hotkeys(self, hk_start,hk_pause,hk_add,hk_finish,hk_dry):
        self.s.hk_start_stop=normalize_hotkey(hk_start.get())
        self.s.hk_pause     =normalize_hotkey(hk_pause.get())
        self.s.hk_add       =normalize_hotkey(hk_add.get())
        self.s.hk_finish    =normalize_hotkey(hk_finish.get())
        self.s.hk_dryrun    =normalize_hotkey(hk_dry.get()) or "<f7>"
        self.s.clamp(); self.save_settings(); self.restart_hotkeys(); self.tip("Hotkeys updated.")

    # ----- Bubble -----
    def show_bubble(self):
        if self.win_bubble and self.win_bubble.winfo_exists():
            self.win_bubble.deiconify(); self.win_bubble.lift(); return
        w = tk.Toplevel(self.root); self.win_bubble = w
        w.title("Bubble")
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.overrideredirect(True)

        # UI content
        frm = ttk.Frame(w, padding=8); frm.grid(row=0, column=0)
        # Profile name (loaded sequence)
        self.lbl_profile = ttk.Label(frm, text="Loaded: (none)", font=("Segoe UI", 9))
        self.lbl_profile.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,2))
        # Status + button
        self.lbl_status = ttk.Label(frm, text="Idle", font=("Segoe UI", 10, "bold"))
        self.lbl_status.grid(row=1, column=0, padx=(0,8))
        ttk.Button(frm, text="Start/Stop", command=self.toggle_start_stop).grid(row=1, column=1)

        # Drag anywhere on the bubble
        self._drag = {"x":0, "y":0}
        def start_drag(e):
            self._drag["x"], self._drag["y"] = e.x_root - w.winfo_x(), e.y_root - w.winfo_y()
        def do_drag(e):
            nx, ny = e.x_root - self._drag["x"], e.y_root - self._drag["y"]
            w.geometry(f"+{int(nx)}+{int(ny)}")
        # Bind both to the whole window and its children
        for widget in (w, frm, self.lbl_status, self.lbl_profile):
            widget.bind("<Button-1>", start_drag)
            widget.bind("<B1-Motion>", do_drag)

        # Initial placement (top-right)
        self.root.update_idletasks()
        w.geometry(f"+{self.root.winfo_screenwidth()-240}+40")

        self._bubble_update()

    def _bubble_update(self):
        if self.win_bubble and self.win_bubble.winfo_exists():
            mode="PAUSED" if self.paused else ("RUNNING" if self.running else "Idle")
            self.lbl_status.config(text=mode)
            prof = self.s.current_meta.name or "(none)"
            self.lbl_profile.config(text=f"Loaded: {ellipsis(prof)}")
        self.root.after(300, self._bubble_update)

    # ----- utils -----
    def tip(self, t): print(f"[TIP] {t}")

    def exit_app(self):
        try:
            if self.listener: self.listener.stop()
        except Exception: pass
        try:
            if self.tray_icon: self.tray_icon.stop()
        except Exception: pass
        try:
            self.stop_event.set()
            if self.click_thread and self.click_thread.is_alive():
                self.click_thread.join(timeout=1.5)
        except Exception: pass
        try:
            if self.rec_mouse_listener: self.rec_mouse_listener.stop()
        except Exception: pass
        try:
            if self.rec_kb_listener: self.rec_kb_listener.stop()
        except Exception: pass
        self.root.quit()

# ---- main ----
def main():
    root = tk.Tk()
    app = App(root)
    if not app.s.start_minimized:
        root.after(100, app.show_settings_window)
    root.mainloop()

if __name__ == "__main__":
    main()
