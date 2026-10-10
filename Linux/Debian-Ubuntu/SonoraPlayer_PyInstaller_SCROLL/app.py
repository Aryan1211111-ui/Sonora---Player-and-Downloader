#!/usr/bin/env python3
import json
import importlib
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from urllib.parse import urlparse

APP_NAME = "Sonora Player"
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".webm"}

def bin_dir():
    directory = bundle_root() / "bin"
    return directory if directory.exists() else None

REFERENCE_BACKGROUND = {
    "#090b10": "#f1f0e8", "#07090d": "#e7e6dd", "#0f1218": "#e7e6dd",
    "#10141a": "#f8f8f3", "#10141b": "#fffdf6", "#10151c": "#fffdf6",
    "#11151d": "#e7e6dd", "#121720": "#f8f8f3", "#151a21": "#d8f078",
    "#171c23": "#e7e6dd", "#171c24": "#deddd3", "#171c25": "#e7e6dd",
    "#1d2430": "#e3e6d8", "#202731": "#d8f078", "#202936": "#dedbcf",
    "#222936": "#deddd3", "#232b36": "#dedbcf", "#252b34": "#d8d9cd",
    "#252d39": "#deddd3", "#061005": "#17231d", "#071006": "#17231d",
    "#ffffff": "#d8f078", "#8cff5a": "#d8f078", "#a3ff7d": "#e4f698",
}
REFERENCE_FOREGROUND = {
    "#061005": "#17231d", "#071006": "#17231d", "#090b10": "#17231d",
    "#606976": "#788174", "#687180": "#788174", "#697382": "#788174",
    "#707a88": "#788174", "#7d8795": "#788174", "#7e8795": "#788174",
    "#7f8997": "#788174", "#808895": "#788174", "#8993a1": "#788174",
    "#8cff5a": "#687a48", "#8e97a5": "#788174", "#9099a8": "#788174",
    "#a0a8b6": "#59645a", "#a3ff7d": "#42513d", "#aab2bf": "#687166",
    "#aeb6c2": "#687166", "#dce2eb": "#17231d", "#e4e7ec": "#17231d",
    "#ecf0f6": "#17231d", "#eef1f5": "#17231d", "#f0f3f7": "#17231d",
    "#f2f5f8": "#17231d", "#f7f9fc": "#17231d", "#ffffff": "#17231d",
}


def bundle_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def bundled_bin(name):
    p = bundle_root() / "bin" / name
    return str(p) if p.exists() else shutil.which(name) or name


def app_data_dir():
    p = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Sonora Player"
    p.mkdir(parents=True, exist_ok=True)
    return p


LIBRARY_FILE = app_data_dir() / "library.json"
PLAYLIST_FILE = app_data_dir() / "playlists.json"
SETTINGS_FILE = app_data_dir() / "settings.json"


def fmt(sec):
    try:
        sec = max(0, int(sec))
    except Exception:
        sec = 0
    return f"{sec // 60}:{sec % 60:02d}"


def safe_name(value):
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value or "Audio")
    return value.strip()[:180] or "Audio"


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


class Sonora(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1400x900")
        self.minsize(1050, 700)
        self.configure(bg="#f1f0e8")

        self.library = load_json(LIBRARY_FILE, [])
        self.playlists = load_json(PLAYLIST_FILE, [])
        self.settings = load_json(SETTINGS_FILE, {"volume": 80})
        self.dark_mode_var = tk.BooleanVar(value=self.settings.get("theme") == "dark")
        self.configure(bg="#090b10" if self.dark_mode_var.get() else "#f1f0e8")
        self.queue = []
        self.current = None
        self.position = 0.0
        self.duration = 0.0
        self.play_started = None
        self.player = None
        self.is_paused = False
        self.manual_stop = False
        self.shuffle = False
        self.repeat = False
        self.view = "home"
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.download_var = tk.DoubleVar(value=0)
        self.progress_var = tk.DoubleVar(value=0)
        self.volume_var = tk.IntVar(value=int(self.settings.get("volume", 80)))
        self.pos_var = tk.StringVar(value="0:00")
        self.dur_var = tk.StringVar(value="0:00")
        self.now_title_var = tk.StringVar(value="Nothing playing")
        self.now_artist_var = tk.StringVar(value="Import music to begin")
        self.download_url_var = tk.StringVar()
        self.download_quality_var = tk.StringVar(value="best")
        self.download_mode_var = tk.StringVar(value="audio")
        self.download_search_results = []
        self.download_results_list = None
        self.selected_playlist = None

        self._setup_style()
        self._build_ui()
        self._refresh_all()
        self.after_idle(self._apply_reference_palette)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(250, self._poll_player)

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f1f0e8")
        style.configure("Panel.TFrame", background="#f8f8f3")
        style.configure("TLabel", background="#f1f0e8", foreground="#17231d")
        style.configure("Muted.TLabel", background="#f1f0e8", foreground="#657067")
        style.configure("Title.TLabel", font=("TkDefaultFont", 25, "bold"), background="#f1f0e8", foreground="#17231d")
        style.configure("Section.TLabel", font=("TkDefaultFont", 13, "bold"), background="#f1f0e8", foreground="#17231d")
        style.configure("Accent.TButton", background="#d8f078", foreground="#17231d", borderwidth=0, padding=10, font=("TkDefaultFont", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#e4f698")])
        style.configure("Dark.TButton", background="#e7e6dd", foreground="#17231d", borderwidth=0, padding=8)
        style.map("Dark.TButton", background=[("active", "#deddd3")])
        style.configure("TEntry", fieldbackground="#fffdf6", foreground="#17231d", insertcolor="#17231d")
        style.configure("TCombobox", fieldbackground="#fffdf6", background="#e7e6dd", foreground="#17231d")
        style.configure("TCheckbutton", background="#f1f0e8", foreground="#17231d")
        style.configure("TScrollbar", background="#e7e6dd", troughcolor="#f1f0e8", arrowcolor="#657067")
        style.configure("Horizontal.TProgressbar", troughcolor="#d8d9cd", background="#829360", bordercolor="#d8d9cd", lightcolor="#829360", darkcolor="#829360")
        style.configure("Horizontal.TScale", background="#f8f8f3", troughcolor="#d8d9cd")
        if self.dark_mode_var.get():
            style.configure("TFrame", background="#090b10")
            style.configure("Panel.TFrame", background="#121720")
            style.configure("TLabel", background="#090b10", foreground="#f7f9fc")
            style.configure("Muted.TLabel", background="#090b10", foreground="#9099a8")
            style.configure("Title.TLabel", background="#090b10", foreground="#f7f9fc")
            style.configure("Section.TLabel", background="#090b10", foreground="#f7f9fc")
            style.configure("Dark.TButton", background="#171c23", foreground="#dce2eb")
            style.map("Dark.TButton", background=[("active", "#252d39")])
            style.configure("TEntry", fieldbackground="#171c23", foreground="#ffffff", insertcolor="#ffffff")
            style.configure("TCombobox", fieldbackground="#171c23", background="#252d39", foreground="#ffffff")
            style.configure("TCheckbutton", background="#121720", foreground="#f7f9fc")
            style.configure("TScrollbar", background="#252d39", troughcolor="#121720", arrowcolor="#aab2bf")
            style.configure("Horizontal.TProgressbar", troughcolor="#252d39")
            style.configure("Horizontal.TScale", background="#121720", troughcolor="#252d39")

    def _apply_reference_palette(self):
        if self.dark_mode_var.get():
            return
        background_options = ("background", "activebackground", "highlightbackground", "selectbackground", "troughcolor")
        foreground_options = ("foreground", "activeforeground", "disabledforeground", "insertbackground", "selectforeground")
        widgets = [self]
        while widgets:
            widget = widgets.pop()
            widgets.extend(widget.winfo_children())
            for option, palette in ((background_options, REFERENCE_BACKGROUND), (foreground_options, REFERENCE_FOREGROUND)):
                for name in option:
                    try:
                        color = widget.cget(name).lower()
                        replacement = palette.get(color)
                        if replacement:
                            widget.configure(**{name: replacement})
                    except (tk.TclError, AttributeError):
                        pass

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        self.sidebar = tk.Frame(self, bg="#07090d", width=235)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        brand = tk.Frame(self.sidebar, bg="#07090d")
        brand.pack(fill="x", padx=17, pady=(22, 25))
        tk.Label(brand, text="S", bg="#8cff5a", fg="#061005", width=2, height=1, font=("TkDefaultFont", 18, "bold"), relief="flat").pack(side="left")
        tk.Label(brand, text=" SONORA", bg="#07090d", fg="#f2f5f8", font=("TkDefaultFont", 14, "bold")).pack(side="left")

        self.nav_buttons = {}
        for key, label, icon in [("home", "Home", "⌂"), ("library", "Your Library", "♫"), ("downloads", "Downloads", "⇩"), ("queue", "Queue", "☷"), ("settings", "Settings", "⚙")]:
            b = tk.Button(self.sidebar, text=f"  {icon}   {label}", anchor="w", bd=0, relief="flat", bg="#07090d", fg="#a0a8b6", activebackground="#171c23", activeforeground="#ffffff", font=("TkDefaultFont", 10), padx=12, pady=11, command=lambda k=key: self.show_view(k))
            b.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = b

        pl_head = tk.Frame(self.sidebar, bg="#07090d")
        pl_head.pack(fill="x", padx=17, pady=(26, 5))
        tk.Label(pl_head, text="PLAYLISTS", bg="#07090d", fg="#687180", font=("TkDefaultFont", 9, "bold")).pack(side="left")
        tk.Button(pl_head, text="+", bd=0, bg="#07090d", fg="#a0a8b6", activebackground="#07090d", activeforeground="#ffffff", font=("TkDefaultFont", 14, "bold"), command=self.new_playlist).pack(side="right")
        self.playlist_sidebar = tk.Frame(self.sidebar, bg="#07090d")
        self.playlist_sidebar.pack(fill="both", expand=True, padx=10)

        bottom = tk.Frame(self.sidebar, bg="#07090d")
        bottom.pack(fill="x", padx=12, pady=12)
        ttk.Button(bottom, text="＋ Import Music", style="Accent.TButton", command=self.import_files).pack(fill="x")
        ttk.Button(bottom, text="▣ Import Folder", style="Dark.TButton", command=self.import_folder).pack(fill="x", pady=(7, 0))

        self.main = tk.Frame(self, bg="#090b10")
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.rowconfigure(1, weight=1)
        self.main.columnconfigure(0, weight=1)

        header = tk.Frame(self.main, bg="#090b10", height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Button(header, text="‹", width=3, bd=0, bg="#171c23", fg="#dce2eb", command=lambda: None).pack(side="left", padx=(22, 7), pady=17)
        tk.Button(header, text="›", width=3, bd=0, bg="#171c23", fg="#dce2eb", command=lambda: None).pack(side="left", padx=0, pady=17)
        search = tk.Entry(header, textvariable=self.search_var, bg="#171c23", fg="#ffffff", insertbackground="#ffffff", relief="flat", bd=0, font=("TkDefaultFont", 10))
        search.pack(side="left", fill="x", expand=False, padx=16, pady=17, ipadx=12, ipady=8)
        search.configure(width=50)
        search.bind("<KeyRelease>", lambda e: self.render_content())

        self.content = tk.Frame(self.main, bg="#090b10")
        self.content.grid(row=1, column=0, sticky="nsew")

        self.right = tk.Frame(self, bg="#0f1218", width=300)
        self.right.grid(row=0, column=2, sticky="nsew")
        self.right.grid_propagate(False)
        tk.Label(self.right, text="NOW PLAYING", bg="#0f1218", fg="#eef1f5", font=("TkDefaultFont", 11, "bold")).pack(anchor="w", padx=20, pady=(22, 15))
        self.big_art = tk.Label(self.right, text="♪", bg="#1d2430", fg="#8cff5a", font=("TkDefaultFont", 68, "bold"), width=5, height=2)
        self.big_art.pack(fill="x", padx=20)
        tk.Label(self.right, textvariable=self.now_title_var, bg="#0f1218", fg="#f7f9fc", font=("TkDefaultFont", 14, "bold"), anchor="w").pack(fill="x", padx=20, pady=(15, 2))
        tk.Label(self.right, textvariable=self.now_artist_var, bg="#0f1218", fg="#9099a8", anchor="w").pack(fill="x", padx=20)
        qh = tk.Frame(self.right, bg="#0f1218")
        qh.pack(fill="x", padx=20, pady=(28, 7))
        tk.Label(qh, text="UP NEXT", bg="#0f1218", fg="#f0f3f7", font=("TkDefaultFont", 10, "bold")).pack(side="left")
        tk.Button(qh, text="Clear", bd=0, bg="#0f1218", fg="#8cff5a", command=self.clear_queue).pack(side="right")
        self.queue_frame = tk.Frame(self.right, bg="#0f1218")
        self.queue_frame.pack(fill="both", expand=True, padx=14)

        self.playerbar = tk.Frame(self, bg="#10141a", height=95)
        self.playerbar.grid(row=1, column=1, columnspan=2, sticky="ew")
        self.playerbar.grid_propagate(False)
        self.playerbar.columnconfigure(1, weight=1)

        current = tk.Frame(self.playerbar, bg="#10141a")
        current.grid(row=0, column=0, sticky="w", padx=18)
        self.mini_art = tk.Label(current, text="♪", bg="#232b36", fg="#8cff5a", width=4, height=2, font=("TkDefaultFont", 14, "bold"))
        self.mini_art.pack(side="left")
        info = tk.Frame(current, bg="#10141a")
        info.pack(side="left", padx=10)
        self.player_title = tk.Label(info, text="Nothing playing", bg="#10141a", fg="#f7f9fc", font=("TkDefaultFont", 9, "bold"))
        self.player_title.pack(anchor="w")
        self.player_artist = tk.Label(info, text="—", bg="#10141a", fg="#9099a8", font=("TkDefaultFont", 8))
        self.player_artist.pack(anchor="w")

        center = tk.Frame(self.playerbar, bg="#10141a")
        center.grid(row=0, column=1, sticky="ew", padx=10)
        controls = tk.Frame(center, bg="#10141a")
        controls.pack()
        self.shuffle_btn = tk.Button(controls, text="⤨", bd=0, bg="#10141a", fg="#aab2bf", command=self.toggle_shuffle)
        self.shuffle_btn.pack(side="left", padx=9)
        tk.Button(controls, text="|‹", bd=0, bg="#10141a", fg="#e4e7ec", command=self.previous).pack(side="left", padx=8)
        self.play_btn = tk.Button(controls, text="▶", bg="#ffffff", fg="#090b10", bd=0, width=3, height=1, font=("TkDefaultFont", 11, "bold"), command=self.toggle_play)
        self.play_btn.pack(side="left", padx=11)
        tk.Button(controls, text="›|", bd=0, bg="#10141a", fg="#e4e7ec", command=self.next_track).pack(side="left", padx=8)
        self.repeat_btn = tk.Button(controls, text="↻", bd=0, bg="#10141a", fg="#aab2bf", command=self.toggle_repeat)
        self.repeat_btn.pack(side="left", padx=9)
        row = tk.Frame(center, bg="#10141a")
        row.pack(fill="x", pady=4)
        tk.Label(row, textvariable=self.pos_var, bg="#10141a", fg="#808895", font=("TkDefaultFont", 8), width=5).pack(side="left")
        self.seek = ttk.Scale(row, from_=0, to=100, orient="horizontal", variable=self.progress_var, command=self.seek_preview)
        self.seek.pack(side="left", fill="x", expand=True)
        tk.Label(row, textvariable=self.dur_var, bg="#10141a", fg="#808895", font=("TkDefaultFont", 8), width=5).pack(side="left")

        vol = tk.Frame(self.playerbar, bg="#10141a")
        vol.grid(row=0, column=2, sticky="e", padx=20)
        tk.Label(vol, text="🔊", bg="#10141a", fg="#dce2eb").pack(side="left", padx=(0, 7))
        ttk.Scale(vol, from_=0, to=100, orient="horizontal", variable=self.volume_var, command=self.volume_changed, length=100).pack(side="left")

    # ---------- persistence / metadata ----------
    def save(self):
        save_json(LIBRARY_FILE, self.library)
        save_json(PLAYLIST_FILE, self.playlists)
        save_json(SETTINGS_FILE, self.settings)

    def probe(self, path):
        ffprobe = bundled_bin("ffprobe")
        try:
            out = subprocess.check_output([ffprobe, "-v", "error", "-show_entries", "format=duration:format_tags=title,artist,album", "-of", "json", path], stderr=subprocess.DEVNULL, text=True, timeout=8)
            data = json.loads(out).get("format", {})
            tags = data.get("tags", {}) or {}
            duration = float(data.get("duration", 0) or 0)
            return {"title": tags.get("title") or Path(path).stem, "artist": tags.get("artist") or "Local audio", "album": tags.get("album") or "Imported", "duration": duration}
        except Exception:
            return {"title": Path(path).stem, "artist": "Local audio", "album": "Imported", "duration": 0}

    def make_song(self, path):
        meta = self.probe(path)
        return {"id": os.path.abspath(path), "path": os.path.abspath(path), **meta}

    def add_paths(self, paths):
        added = 0
        for p in paths:
            if os.path.isfile(p) and Path(p).suffix.lower() in AUDIO_EXTS and not any(s.get("path") == os.path.abspath(p) for s in self.library):
                self.library.append(self.make_song(p))
                added += 1
        self.save()
        self._refresh_all()
        self.status_var.set(f"Added {added} track(s)")

    # ---------- navigation ----------
    def show_view(self, view):
        self.view = view
        for k, b in self.nav_buttons.items():
            b.configure(bg="#151a21" if k == view else "#07090d", fg="#ffffff" if k == view else "#a0a8b6")
        self.render_content()

    def _refresh_all(self):
        self.render_playlists_sidebar()
        self.render_content()
        self.render_queue()

    def render_playlists_sidebar(self):
        self.after_idle(self._apply_reference_palette)
        for w in self.playlist_sidebar.winfo_children(): w.destroy()
        if not self.playlists:
            tk.Label(self.playlist_sidebar, text="No playlists yet", bg="#07090d", fg="#606976").pack(anchor="w", padx=8, pady=4)
            return
        for i,p in enumerate(self.playlists):
            b = tk.Button(self.playlist_sidebar, text="▱  " + p["name"], anchor="w", bd=0, bg="#07090d", fg="#a0a8b6", activebackground="#151a21", activeforeground="#ffffff", command=lambda i=i: self.show_playlist(i))
            b.pack(fill="x", pady=1)

    def render_content(self):
        self.after_idle(self._apply_reference_palette)
        for w in self.content.winfo_children(): w.destroy()
        query = self.search_var.get().strip().lower()
        if self.view == "downloads": return self.render_downloads()
        if self.view == "queue": return self.render_queue_page()
        if self.view == "settings": return self.render_settings()
        songs = [s for s in self.library if not query or query in " ".join([s.get("title",""),s.get("artist",""),s.get("album","")]).lower()]
        if self.view == "home":
            self.render_home(songs)
        elif self.view == "library":
            self.render_library(songs)

    def section_header(self, title, subtitle=""):
        f=tk.Frame(self.content,bg="#090b10"); f.pack(fill="x", padx=30, pady=(22,14))
        tk.Label(f,text=title,bg="#090b10",fg="#f7f9fc",font=("TkDefaultFont",25,"bold"),wraplength=760,justify="left").pack(anchor="w")
        if subtitle: tk.Label(f,text=subtitle,bg="#090b10",fg="#9099a8").pack(anchor="w",pady=(7,0))

    def render_home(self,songs):
        self.section_header("Your music, right where you left it.",f"{len(self.library)} tracks in your library")
        actions=tk.Frame(self.content,bg="#090b10"); actions.pack(fill="x",padx=30,pady=(0,22))
        ttk.Button(actions,text="＋ Import Music",style="Accent.TButton",command=self.import_files).pack(side="left")
        ttk.Button(actions,text="⇩ Open Downloader",style="Dark.TButton",command=lambda:self.show_view("downloads")).pack(side="left",padx=8)
        tk.Label(self.content,text="RECENTLY ADDED",bg="#090b10",fg="#687180",font=("TkDefaultFont",9,"bold")).pack(anchor="w",padx=30,pady=(0,10))
        self.render_cards(songs[:6])
        tk.Label(self.content,text="YOUR LIBRARY",bg="#090b10",fg="#687180",font=("TkDefaultFont",9,"bold")).pack(anchor="w",padx=30,pady=(22,9))
        self.render_song_list(songs)

    def render_library(self,songs):
        self.section_header("Your Library",f"{len(songs)} song(s)")
        self.render_song_list(songs)

    def render_cards(self,songs):
        frame=tk.Frame(self.content,bg="#090b10"); frame.pack(fill="x",padx=30)
        for i,s in enumerate(songs[:3]):
            card=tk.Frame(frame,bg="#121720",width=160,height=185); card.grid(row=0,column=i,padx=(0,14)); card.grid_propagate(False)
            art_colors=("#d8e1ce","#eadbc7","#d8ddd9")
            art=tk.Label(card,text="♫",bg=art_colors[i % len(art_colors)],fg="#536048",font=("TkDefaultFont",36,"bold")); art.pack(fill="x",ipady=19)
            tk.Label(card,text=s["title"],bg="#121720",fg="#ffffff",anchor="w",font=("TkDefaultFont",9,"bold"),wraplength=138).pack(fill="x",padx=10,pady=(9,2))
            tk.Label(card,text=s.get("artist",""),bg="#121720",fg="#9099a8",anchor="w").pack(fill="x",padx=10)
            card.bind("<Double-Button-1>",lambda e,s=s:self.play_song(s))
            art.bind("<Double-Button-1>",lambda e,s=s:self.play_song(s))

    def render_song_list(self,songs,parent=None):
        parent=parent or self.content
        outer=tk.Frame(parent,bg="#090b10"); outer.pack(fill="both",expand=True,padx=30,pady=(0,20))
        if not songs:
            tk.Label(outer,text="No music here yet",bg="#090b10",fg="#7e8795",font=("TkDefaultFont",14)).pack(pady=55)
            return

        # Dedicated scrollable music area. The player/header/sidebar remain fixed.
        canvas=tk.Canvas(outer,bg="#090b10",highlightthickness=0,bd=0)
        scrollbar=ttk.Scrollbar(outer,orient="vertical",command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right",fill="y")
        canvas.pack(side="left",fill="both",expand=True)

        frame=tk.Frame(canvas,bg="#090b10")
        window_id=canvas.create_window((0,0),window=frame,anchor="nw")

        def on_frame_configure(_=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def on_canvas_configure(event):
            canvas.itemconfigure(window_id,width=event.width)
        frame.bind("<Configure>",on_frame_configure)
        canvas.bind("<Configure>",on_canvas_configure)

        def wheel(event):
            if event.delta:
                canvas.yview_scroll(int(-event.delta/120), "units")
            elif event.num==4:
                canvas.yview_scroll(-3, "units")
            elif event.num==5:
                canvas.yview_scroll(3, "units")
        canvas.bind_all("<MouseWheel>",wheel,add="+")
        canvas.bind_all("<Button-4>",wheel,add="+")
        canvas.bind_all("<Button-5>",wheel,add="+")

        for idx,s in enumerate(songs):
            row=tk.Frame(frame,bg="#10151c"); row.pack(fill="x",pady=2)
            tk.Label(row,text=str(idx+1),width=4,bg="#10151c",fg="#697382").pack(side="left")
            tk.Label(row,text="♪",width=4,bg="#10151c",fg="#8cff5a",font=("TkDefaultFont",13,"bold")).pack(side="left")
            info=tk.Frame(row,bg="#10151c"); info.pack(side="left",fill="x",expand=True,pady=8)
            tk.Label(info,text=s["title"],bg="#10151c",fg="#ffffff",font=("TkDefaultFont",10,"bold"),anchor="w").pack(fill="x")
            tk.Label(info,text=f'{s.get("artist","Local audio")}  •  {fmt(s.get("duration",0))}',bg="#10151c",fg="#8e97a5",anchor="w").pack(fill="x")
            ttk.Button(row,text="▶",style="Dark.TButton",command=lambda s=s:self.play_song(s)).pack(side="right",padx=4)
            ttk.Button(row,text="＋",style="Dark.TButton",command=lambda s=s:self.add_to_queue(s)).pack(side="right",padx=4)
            ttk.Button(row,text="☷",style="Dark.TButton",command=lambda s=s:self.add_to_playlist_dialog(s)).pack(side="right",padx=4)

    # ---------- queue ----------
    def add_to_queue(self,s):
        self.queue.append(s)
        self.render_queue()
        self.status_var.set(f"Queued: {s['title']}")

    def clear_queue(self):
        self.queue=[]
        self.render_queue()

    def render_queue(self):
        self.after_idle(self._apply_reference_palette)
        for w in self.queue_frame.winfo_children(): w.destroy()
        if not self.queue:
            tk.Label(self.queue_frame,text="Nothing queued.",bg="#0f1218",fg="#707a88").pack(anchor="w",pady=8)
            return
        for i,s in enumerate(self.queue[:18]):
            f=tk.Frame(self.queue_frame,bg="#0f1218"); f.pack(fill="x",pady=3)
            tk.Label(f,text="♪",width=3,bg="#202731",fg="#8cff5a").pack(side="left",ipady=4)
            t=tk.Frame(f,bg="#0f1218"); t.pack(side="left",fill="x",expand=True,padx=8)
            tk.Label(t,text=s["title"],bg="#0f1218",fg="#eef1f5",anchor="w",font=("TkDefaultFont",9,"bold")).pack(fill="x")
            tk.Label(t,text=s.get("artist",""),bg="#0f1218",fg="#7f8997",anchor="w").pack(fill="x")
            f.bind("<Double-Button-1>",lambda e,i=i:self.play_queue_index(i))

    def render_queue_page(self):
        self.section_header("Queue",f"{len(self.queue)} track(s) waiting")
        if self.queue:
            self.render_song_list(self.queue)
        else:
            tk.Label(self.content,text="Add songs to your queue with the ＋ button.",bg="#090b10",fg="#7f8997").pack(pady=55)

    def play_queue_index(self,i):
        if 0<=i<len(self.queue): self.play_song(self.queue[i])

    # ---------- playlists ----------
    def new_playlist(self):
        name=simpledialog.askstring("New Playlist","Playlist name:",parent=self)
        if name and name.strip():
            self.playlists.append({"name":name.strip(),"songs":[]})
            self.save(); self.render_playlists_sidebar(); self.status_var.set("Playlist created")

    def show_playlist(self,i):
        self.selected_playlist=i
        self.view="library"
        for k,b in self.nav_buttons.items(): b.configure(bg="#151a21" if k=="library" else "#07090d", fg="#ffffff" if k=="library" else "#a0a8b6")
        for w in self.content.winfo_children(): w.destroy()
        p=self.playlists[i]
        songs=[next((s for s in self.library if s["id"]==sid),None) for sid in p["songs"]]
        songs=[s for s in songs if s]
        self.section_header(p["name"],f"{len(songs)} track(s)")
        self.render_song_list(songs)

    def add_to_playlist_dialog(self,s):
        if not self.playlists:
            messagebox.showinfo("No playlists","Create a playlist first.",parent=self); return
        win=tk.Toplevel(self); win.title("Add to playlist"); win.configure(bg="#10141a"); win.resizable(False,False)
        tk.Label(win,text=f"Add “{s['title']}” to:",bg="#10141a",fg="#ffffff",font=("TkDefaultFont",11,"bold")).pack(padx=20,pady=(18,10))
        for i,p in enumerate(self.playlists):
            tk.Button(win,text=p["name"],anchor="w",width=35,bd=0,bg="#171c24",fg="#ffffff",activebackground="#252d39",command=lambda i=i:self._playlist_add(win,i,s)).pack(padx=20,pady=3)

    def _playlist_add(self,win,i,s):
        if s["id"] not in self.playlists[i]["songs"]:
            self.playlists[i]["songs"].append(s["id"]); self.save(); self.status_var.set("Added to playlist")
        win.destroy(); self.render_playlists_sidebar()

    # ---------- downloader ----------
    def render_downloads(self):
        self.section_header("Find and download","Search YouTube by song or video title, then choose a result and format.")
        box=tk.Frame(self.content,bg="#f8f8f3"); box.pack(fill="x",padx=30,pady=5)
        tk.Label(box,text="SEARCH YOUTUBE OR PASTE A VIDEO LINK",bg="#f8f8f3",fg="#536048",font=("TkDefaultFont",9,"bold")).pack(anchor="w",padx=22,pady=(20,7))
        search_row=tk.Frame(box,bg="#f8f8f3"); search_row.pack(fill="x",padx=22)
        entry=tk.Entry(search_row,textvariable=self.download_url_var,bg="#fffdf6",fg="#17231d",insertbackground="#17231d",relief="flat",bd=0)
        entry.pack(side="left",fill="x",expand=True,ipady=12)
        entry.bind("<KeyRelease>",self._clear_download_results)
        ttk.Button(search_row,text="Search YouTube",style="Dark.TButton",command=self.search_youtube).pack(side="left",padx=(9,0))
        self.search_loading_frame=tk.Frame(box,bg="#f8f8f3")
        tk.Label(self.search_loading_frame,text="Please wait...",bg="#f8f8f3",fg="#657067").pack(side="left")
        self.search_loading_bar=ttk.Progressbar(self.search_loading_frame,mode="indeterminate",length=120)
        self.search_loading_bar.pack(side="left",padx=(10,0))
        self.download_results_list=tk.Listbox(box,height=5,selectmode=tk.SINGLE,exportselection=False,activestyle="none",bg="#fffdf6",fg="#17231d",selectbackground="#d8f078",selectforeground="#17231d",relief="flat",bd=0,font=("TkDefaultFont",10))
        self.download_results_list.pack(fill="x",padx=22,pady=(10,0))
        self.search_loading_frame.pack_forget()
        self.download_results_list.bind("<Double-Button-1>",lambda _event:self.start_download())
        controls=tk.Frame(box,bg="#f8f8f3"); controls.pack(fill="x",padx=22,pady=14)
        format_row=tk.Frame(controls,bg="#f8f8f3"); format_row.pack(fill="x",pady=(0,10))
        tk.Label(format_row,text="FORMAT",bg="#f8f8f3",fg="#536048",font=("TkDefaultFont",9,"bold")).pack(side="left",padx=(0,7))
        tk.Radiobutton(format_row,text="Audio · MP3",variable=self.download_mode_var,value="audio",bg="#f8f8f3",fg="#17231d",activebackground="#f8f8f3",selectcolor="#d8f078",command=self._update_download_quality).pack(side="left")
        tk.Radiobutton(format_row,text="Video · MP4",variable=self.download_mode_var,value="video",bg="#f8f8f3",fg="#17231d",activebackground="#f8f8f3",selectcolor="#d8f078",command=self._update_download_quality).pack(side="left",padx=(8,12))
        quality_row=tk.Frame(controls,bg="#f8f8f3"); quality_row.pack(fill="x")
        tk.Label(quality_row,text="QUALITY",bg="#f8f8f3",fg="#536048",font=("TkDefaultFont",9,"bold")).pack(side="left",padx=(0,7))
        self.download_quality_combo=ttk.Combobox(quality_row,textvariable=self.download_quality_var,state="readonly",width=17)
        self.download_quality_combo.pack(side="left",padx=(0,9))
        self._update_download_quality()
        ttk.Button(quality_row,text="Download selected",style="Accent.TButton",command=self.start_download).pack(side="left")
        tk.Label(box,text="Audio is saved as MP3; videos are saved as MP4. Source quality may limit the selected output quality.",bg="#f8f8f3",fg="#788174",font=("TkDefaultFont",9),anchor="w",wraplength=760,justify="left").pack(fill="x",padx=22,pady=(0,8))
        self.download_label=tk.Label(box,textvariable=self.status_var,bg="#f8f8f3",fg="#657067",anchor="w")
        self.download_label.pack(fill="x",padx=22,pady=(2,12))
        ttk.Progressbar(box,variable=self.download_var,maximum=100,style="Horizontal.TProgressbar").pack(fill="x",padx=22,pady=(0,18))
        tk.Label(self.content,text="Downloads are saved to ~/Music/Sonora Downloads. Only download content you own or are authorized to save; respect YouTube’s terms and creators’ rights.",bg="#f1f0e8",fg="#788174",wraplength=780,justify="left").pack(anchor="w",padx=30,pady=18)

    def _set_search_loading(self,loading):
        if loading:
            self.search_loading_frame.pack(fill="x",padx=22,pady=(10,0),before=self.download_results_list)
            self.search_loading_bar.start(12)
        else:
            self.search_loading_bar.stop()
            self.search_loading_frame.pack_forget()

    def _update_download_quality(self):
        if not getattr(self,"download_quality_combo",None):
            return
        if self.download_mode_var.get()=="video":
            values=("1080p","720p","320p","240p","144p","Best available")
        else:
            values=("320 kbps","256 kbps","192 kbps","160 kbps","128 kbps","96 kbps","64 kbps","48 kbps","32 kbps","Best available")
        self.download_quality_combo.configure(values=values)
        self.download_quality_var.set(values[0])

    def _clear_download_results(self,_event=None):
        self.download_search_results=[]
        if self.download_results_list:
            self.download_results_list.delete(0,tk.END)

    def _is_youtube_url(self,value):
        host=(urlparse(value).hostname or "").lower().removeprefix("www.")
        return host in {"youtube.com","m.youtube.com","music.youtube.com","youtu.be"}

    def search_youtube(self):
        query=self.download_url_var.get().strip()
        if not query:
            messagebox.showwarning("Missing search","Enter a song or video title first.",parent=self)
            return
        if query.startswith(("http://","https://")) and not self._is_youtube_url(query):
            messagebox.showwarning("Unsupported link","Paste a YouTube video link or search by title.",parent=self)
            return
        try:
            yt_dlp=importlib.import_module("yt_dlp")
        except Exception:
            messagebox.showerror("Downloader unavailable","Install yt-dlp or rebuild Sonora so yt-dlp is bundled.",parent=self)
            return
        self._clear_download_results()
        self._set_search_loading(True)
        self.status_var.set("Searching YouTube…")

        def worker():
            try:
                target=query if query.startswith(("http://","https://")) else f"ytsearch5:{query}"
                options={"quiet":True,"no_warnings":True,"extract_flat":"in_playlist","skip_download":True,"noplaylist":True}
                with yt_dlp.YoutubeDL(options) as ydl:
                    info=ydl.extract_info(target,download=False)
                results=list(info.get("entries") or []) if info else []
                if info and not results and info.get("id"):
                    results=[info]
                self.after(0,lambda items=results:self._show_download_results(items))
            except Exception as error:
                self.after(0,lambda detail=str(error):self._download_search_failed(detail))

        threading.Thread(target=worker,daemon=True).start()

    def _show_download_results(self,results):
        self._set_search_loading(False)
        self.download_search_results=results
        self.download_results_list.delete(0,tk.END)
        for result in results:
            title=result.get("title") or "Untitled video"
            uploader=result.get("uploader") or result.get("channel") or "YouTube"
            duration=fmt(result.get("duration",0)) if result.get("duration") else "Duration unknown"
            self.download_results_list.insert(tk.END,f"{title}  ·  {uploader}  ·  {duration}")
        if results:
            self.status_var.set(f"Found {len(results)} result(s). Select one to download.")
        else:
            self.status_var.set("No results found. Try another title.")

    def _download_search_failed(self,detail):
        self._set_search_loading(False)
        self.status_var.set("YouTube search failed")
        messagebox.showerror("YouTube search failed",detail[:300],parent=self)

    def start_download(self):
        query=self.download_url_var.get().strip()
        selection=self.download_results_list.curselection() if self.download_results_list else ()
        if selection and selection[0]<len(self.download_search_results):
            result=self.download_search_results[selection[0]]
            url=result.get("webpage_url") or result.get("original_url") or result.get("url") or ""
            if url and not url.startswith(("http://","https://")) and result.get("id"):
                url=f"https://www.youtube.com/watch?v={result['id']}"
        elif query.startswith(("http://","https://")):
            url=query
        else:
            messagebox.showwarning("Choose a result","Search YouTube and select a result before downloading.",parent=self)
            return
        if not url:
            messagebox.showwarning("Missing video","The selected result does not have a downloadable video URL.",parent=self)
            return
        if url.startswith(("http://","https://")) and not self._is_youtube_url(url):
            messagebox.showwarning("Unsupported link","Only YouTube video links are supported.",parent=self)
            return
        try:
            yt_dlp=importlib.import_module("yt_dlp")
        except Exception:
            messagebox.showerror("Downloader unavailable","Install yt-dlp or rebuild Sonora so yt-dlp is bundled.",parent=self); return
        out_dir=Path.home()/"Music"/"Sonora Downloads"
        out_dir.mkdir(parents=True,exist_ok=True)
        self.download_var.set(0); self.status_var.set("Starting download…")
        q=self.download_quality_var.get()
        mode=self.download_mode_var.get()
        if mode=="video":
            height=q.removesuffix("p") if q!="Best available" else None
            quality=f"bestvideo[height<={height}]+bestaudio/best[height<={height}]" if height else "bestvideo+bestaudio/best"
        else:
            bitrate=q.split(" ",1)[0] if q!="Best available" else None
            quality="bestaudio/best"

        def worker():
            last_file=None
            def hook(d):
                nonlocal last_file
                if d.get("status")=="downloading":
                    total=d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    done=d.get("downloaded_bytes") or 0
                    pct=(done/total*100) if total else 0
                    self.after(0,lambda pct=pct:self.download_var.set(pct))
                    self.after(0,lambda:self.status_var.set(f"Downloading… {pct:.0f}%"))
                elif d.get("status")=="finished":
                    last_file=d.get("filename")
                    message="Converting audio…" if mode=="audio" else "Finalizing video…"
                    self.after(0,lambda text=message:self.status_var.set(text))
            opts={
                "format":quality,
                "noplaylist":True,
                "ffmpeg_location": str(bin_dir()) if bin_dir() else None,
                "outtmpl":str(out_dir/"%(title)s.%(ext)s"),
                "progress_hooks":[hook],
                "quiet":True,
                "no_warnings":True,
            }
            if mode=="audio":
                opts["postprocessors"]=[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":bitrate or "0"}]
            else:
                opts["merge_output_format"]="mp4"
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info=ydl.extract_info(url,download=True)
                    prepared=Path(ydl.prepare_filename(info))
                    requested=info.get("requested_downloads") or []
                    requested_path=Path(requested[-1]["filepath"]) if requested and requested[-1].get("filepath") else None
                    if mode=="audio":
                        candidates=[prepared.with_suffix(".mp3"),requested_path,prepared,Path(last_file) if last_file else None]
                    else:
                        candidates=[prepared.with_suffix(".mp4"),requested_path,prepared,Path(last_file) if last_file else None]
                saved_file=next((path for path in candidates if path and path.exists()),None)
                if saved_file and mode=="audio":
                    song=self.make_song(str(saved_file))
                    self.after(0,lambda s=song:self._download_complete(s))
                elif saved_file:
                    self.after(0,lambda path=saved_file:self._video_download_complete(path))
                else:
                    self.after(0,lambda:self.status_var.set("Download finished, but the output file was not found."))
            except Exception as e:
                self.after(0,lambda msg=str(e):self.status_var.set("Download failed: "+msg[:220]))
        threading.Thread(target=worker,daemon=True).start()

    def _video_download_complete(self,path):
        self.download_var.set(100)
        self.status_var.set(f"Video saved: {path.name}")

    def _download_complete(self,s):
        if not any(x["path"]==s["path"] for x in self.library): self.library.append(s)
        self.save(); self.download_var.set(100); self.status_var.set("✓ Download complete and added to library"); self._refresh_all()

    # ---------- playback ----------
    def play_song(self,s,offset=0):
        self._stop_process()
        self.current=s
        self.position=max(0,min(float(offset),float(s.get("duration",0) or 0)))
        self.duration=float(s.get("duration",0) or 0)
        if not self.duration:
            self.duration=float(self.probe(s["path"]).get("duration",0) or 0)
            s["duration"]=self.duration; self.save()
        self.is_paused=False
        self.manual_stop=False
        self._launch_player(self.position)
        self.update_now_playing()
        self._remove_current_from_queue_if_first()

    def _launch_player(self,offset):
        ffplay=bundled_bin("ffplay")
        if not Path(self.current["path"]).exists():
            messagebox.showerror("File missing",self.current["path"],parent=self); return
        args=[ffplay,"-nodisp","-autoexit","-loglevel","error","-volume",str(self.volume_var.get())]
        if offset>0: args += ["-ss",str(offset)]
        args += [self.current["path"]]
        try:
            self.player=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.play_started=time.monotonic()
            self.play_btn.configure(text="Ⅱ")
        except Exception as e:
            self.player=None
            messagebox.showerror("Playback error",str(e),parent=self)

    def _remove_current_from_queue_if_first(self):
        if self.queue and self.queue[0].get("id")==self.current.get("id"):
            self.queue.pop(0)
        self.render_queue()

    def _stop_process(self):
        if self.player and self.player.poll() is None:
            try:self.player.terminate()
            except Exception:pass
        self.player=None

    def toggle_play(self):
        if not self.current:
            if self.library: self.play_song(self.library[0])
            return
        if self.player and self.player.poll() is None:
            self.position=self.current_position()
            self._stop_process()
            self.is_paused=True
            self.play_btn.configure(text="▶")
        else:
            self.is_paused=False
            self._launch_player(self.position)

    def stop(self):
        self.position=0; self._stop_process(); self.is_paused=False; self.play_btn.configure(text="▶")

    def toggle_shuffle(self):
        self.shuffle=not self.shuffle; self.shuffle_btn.configure(fg="#8cff5a" if self.shuffle else "#aab2bf")

    def toggle_repeat(self):
        self.repeat=not self.repeat; self.repeat_btn.configure(fg="#8cff5a" if self.repeat else "#aab2bf")

    def previous(self):
        if self.current_position()>3:
            self.play_song(self.current,0); return
        pool=self.library if self.view!="queue" else self.queue
        if self.current and pool:
            try:i=next(i for i,x in enumerate(pool) if x["id"]==self.current["id"])-1
            except StopIteration:i=0
            self.play_song(pool[i%len(pool)])

    def next_track(self):
        if self.shuffle:
            choices=[s for s in self.library if not self.current or s["id"]!=self.current["id"]]
            if choices:self.play_song(random.choice(choices)); return
        if self.queue:
            self.play_song(self.queue[0]); return
        if self.current:
            try:i=next(i for i,x in enumerate(self.library) if x["id"]==self.current["id"])+1
            except StopIteration:i=0
            if i < len(self.library): self.play_song(self.library[i])
            elif self.repeat and self.library:self.play_song(self.library[0])

    def current_position(self):
        if self.player and self.play_started is not None and not self.is_paused:
            return min(self.duration,max(0,self.position+(time.monotonic()-self.play_started)))
        return self.position

    def _poll_player(self):
        if self.current:
            p=self.current_position()
            self.progress_var.set((p/self.duration*100) if self.duration else 0)
            self.pos_var.set(fmt(p)); self.dur_var.set(fmt(self.duration))
            if self.player and self.player.poll() is not None:
                ended_pos=p
                self.player=None
                if not self.manual_stop and not self.is_paused:
                    if self.repeat: self.play_song(self.current,0)
                    else: self.next_track()
        self.after(250,self._poll_player)

    def seek_preview(self, value):
        if not self.current or not self.duration:return
        target=float(value)/100*self.duration
        self.pos_var.set(fmt(target))
        # ttk Scale continuously fires while dragging; only restart when released is more complicated.
        # Restarting here gives functional seeking and remains lightweight.
        if self.player and self.player.poll() is None:
            self.position=target; self._stop_process(); self._launch_player(target)
        else:self.position=target

    def volume_changed(self,_=None):
        self.settings["volume"]=int(self.volume_var.get()); self.save()
        if self.current and self.player and self.player.poll() is None:
            pos=self.current_position(); self.position=pos; self._stop_process(); self._launch_player(pos)

    def update_now_playing(self):
        if not self.current:return
        title=self.current.get("title","Unknown"); artist=self.current.get("artist","Local audio")
        self.player_title.configure(text=title); self.player_artist.configure(text=artist)
        self.now_title_var.set(title); self.now_artist_var.set(artist)

    # ---------- import ----------
    def import_files(self):
        paths=filedialog.askopenfilenames(title="Import Music",filetypes=[("Audio","*.mp3 *.wav *.ogg *.m4a *.aac *.flac *.webm"),("All files","*.*")])
        if paths:self.add_paths(paths)

    def import_folder(self):
        folder=filedialog.askdirectory(title="Import Music Folder")
        if not folder:return
        paths=[]
        for r,_,files in os.walk(folder):
            for f in files:
                if Path(f).suffix.lower() in AUDIO_EXTS:paths.append(os.path.join(r,f))
        self.add_paths(paths)

    # ---------- settings ----------
    def render_settings(self):
        self.section_header("Settings","Sonora Player configuration")
        body=tk.Frame(self.content,bg="#090b10"); body.pack(fill="x",padx=30)
        theme_row=tk.Frame(body,bg="#121720"); theme_row.pack(fill="x",pady=2)
        theme_info=tk.Frame(theme_row,bg="#121720"); theme_info.pack(side="left",fill="x",expand=True,padx=18,pady=16)
        tk.Label(theme_info,text="Appearance",bg="#121720",fg="#ffffff",font=("TkDefaultFont",10,"bold")).pack(anchor="w")
        tk.Label(theme_info,text="Choose a light or dark interface.",bg="#121720",fg="#8993a1").pack(anchor="w",pady=(4,0))
        ttk.Checkbutton(theme_row,text="Dark mode",variable=self.dark_mode_var,command=self.apply_theme).pack(side="right",padx=18)
        for title,desc,cmd in [
            ("Music folder","Downloaded audio goes to ~/Music/Sonora Downloads",None),
            ("Clear library","Remove library metadata. Original files are not deleted.",self.clear_library),
        ]:
            row=tk.Frame(body,bg="#121720"); row.pack(fill="x",pady=2)
            info=tk.Frame(row,bg="#121720"); info.pack(side="left",fill="x",expand=True,padx=18,pady=16)
            tk.Label(info,text=title,bg="#121720",fg="#ffffff",font=("TkDefaultFont",10,"bold")).pack(anchor="w")
            tk.Label(info,text=desc,bg="#121720",fg="#8993a1").pack(anchor="w",pady=(4,0))
            if cmd: ttk.Button(row,text="Clear",style="Dark.TButton",command=cmd).pack(side="right",padx=18)

    def apply_theme(self):
        self.settings["theme"] = "dark" if self.dark_mode_var.get() else "light"
        self.save()
        self.configure(bg="#090b10" if self.dark_mode_var.get() else "#f1f0e8")
        self._setup_style()
        for child in self.winfo_children():
            child.destroy()
        self._build_ui()
        self._refresh_all()

    def clear_library(self):
        if messagebox.askyesno("Clear library","Remove all library entries? Your actual music files will stay on disk.",parent=self):
            self.library=[]
            self.save(); self._refresh_all()

    def on_close(self):
        self.manual_stop=True; self._stop_process(); self.destroy()


if __name__=="__main__":
    app=Sonora()
    app.mainloop()
