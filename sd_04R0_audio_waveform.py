"""
sd_05R0_ui_setup_tab.py

Setup tab UI for Shadowing English App (R0),
updated to use AudioWaveformPanel (real waveform + audio playback).

- Table: No, Begin, End, Content, Confirm
- Control bar: prev / current sentence (Play) / pause / next / loop
- Begin/End chỉnh bằng entry + nút ▲▼ + Set (playhead placeholder)
- Waveform: panel bên dưới, có slider t0 + Play/Loop/Stop riêng.
- Khi nhấn "Sentence" (current_sentence_btn) ở Setup Tab:
    => gọi waveform_panel.play_range(begin, end, loop=is_looping)

Main app cần:
-----------
- Gán:
    owner.sentences: list[Sentence]
    owner.current_sentence: int
    owner.audio_path: str | None
    owner.is_looping: bool
    owner.playback_speed: float (chỉ để hiển thị)
    owner.waveform_panel_setup: AudioWaveformPanel (tuỳ ý lưu)
"""

from __future__ import annotations

from typing import Any, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from sd_02R0_models import Sentence, format_time, parse_time
from sd_04R0_audio_waveform import AudioWaveformPanel


class SetupTab:
    """
    Encapsulates all UI and behavior of the Setup tab.

    It does NOT own the data; instead it reads/writes:
    - owner.sentences        (list[Sentence])
    - owner.current_sentence (int)
    - owner.audio_path       (str | None)
    - owner.is_looping       (bool)
    - owner.playback_speed   (float)

    The waveform is handled by AudioWaveformPanel, which is created here.
    """

    def __init__(self, parent: tk.Frame, owner: Any) -> None:
        self.owner = owner

        # Outer frame to pack into Notebook
        self.frame = tk.Frame(parent)

        # Table
        self.tree: ttk.Treeview
        self._create_table_area()

        # Control bar (navigation + begin/end)
        self.begin_entry: Optional[tk.Entry] = None
        self.end_entry: Optional[tk.Entry] = None
        self.current_sentence_btn: Optional[tk.Button] = None
        self.loop_btn: Optional[tk.Button] = None
        self._create_control_bar()

        # Waveform panel (real audio waveform)
        wave_container = tk.Frame(self.frame)
        wave_container.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        self.waveform_panel = AudioWaveformPanel(wave_container)

        # Nếu owner có audio_path sẵn, load luôn
        audio_path = getattr(self.owner, "audio_path", None)
        if audio_path:
            self.waveform_panel.set_audio_path(audio_path)

        # Initial refresh
        self.refresh_all()

    # ------------------------------------------------------------------ #
    # Owner state access
    # ------------------------------------------------------------------ #

    @property
    def sentences(self) -> List[Sentence]:
        return getattr(self.owner, "sentences", [])

    @property
    def current_index(self) -> int:
        return int(getattr(self.owner, "current_sentence", 0))

    @current_index.setter
    def current_index(self, value: int) -> None:
        setattr(self.owner, "current_sentence", int(value))

    @property
    def is_looping(self) -> bool:
        return bool(getattr(self.owner, "is_looping", False))

    @is_looping.setter
    def is_looping(self, value: bool) -> None:
        setattr(self.owner, "is_looping", bool(value))

    @property
    def playback_speed(self) -> float:
        return float(getattr(self.owner, "playback_speed", 1.0))

    # ------------------------------------------------------------------ #
    # UI creation
    # ------------------------------------------------------------------ #

    def _create_table_area(self) -> None:
        table_frame = tk.Frame(self.frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        v_scrollbar = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        h_scrollbar = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        columns = ("No", "Begin", "End", "Content", "Confirm")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
        )

        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)

        self.tree.heading("No", text="No")
        self.tree.heading("Begin", text="Begin")
        self.tree.heading("End", text="End")
        self.tree.heading("Content", text="Content")
        self.tree.heading("Confirm", text="Confirm")

        self.tree.column("No", width=80, anchor=tk.CENTER)
        self.tree.column("Begin", width=100, anchor=tk.CENTER)
        self.tree.column("End", width=100, anchor=tk.CENTER)
        self.tree.column("Content", width=700)
        self.tree.column("Confirm", width=80, anchor=tk.CENTER)

        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<ButtonRelease-1>", self._on_click)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _create_control_bar(self) -> None:
        control_frame = tk.Frame(
            self.frame, bg="lightgray", relief=tk.RAISED, borderwidth=2, height=90
        )
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        control_frame.pack_propagate(False)

        # Left: navigation
        left_frame = tk.Frame(control_frame, bg="lightgray")
        left_frame.pack(side=tk.LEFT, padx=10, pady=10)

        tk.Button(
            left_frame,
            text="◄◄",
            font=("Arial", 14, "bold"),
            width=4,
            command=self.previous_sentence,
            bg="lightgreen",
            relief=tk.RAISED,
            borderwidth=3,
        ).pack(side=tk.LEFT, padx=2)

        self.current_sentence_btn = tk.Button(
            left_frame,
            text="Sentence 1",
            font=("Arial", 14, "bold"),
            width=12,
            command=self.play_current_sentence,
            bg="green",
            fg="white",
            relief=tk.RAISED,
            borderwidth=3,
        )
        self.current_sentence_btn.pack(side=tk.LEFT, padx=2)

        tk.Button(
            left_frame,
            text="❚❚",
            font=("Arial", 14, "bold"),
            width=4,
            command=self.toggle_pause,
            bg="lightgreen",
            relief=tk.RAISED,
            borderwidth=3,
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            left_frame,
            text="►►",
            font=("Arial", 14, "bold"),
            width=4,
            command=self.next_sentence,
            bg="lightgreen",
            relief=tk.RAISED,
            borderwidth=3,
        ).pack(side=tk.LEFT, padx=2)

        self.loop_btn = tk.Button(
            left_frame,
            text="🔁",
            font=("Arial", 12),
            width=4,
            command=self.toggle_loop,
            bg="lightgreen",
            relief=tk.RAISED,
            borderwidth=3,
        )
        self.loop_btn.pack(side=tk.LEFT, padx=2)

        # Center: Begin/End editing
        center_frame = tk.Frame(control_frame, bg="lightgray")
        center_frame.pack(side=tk.LEFT, padx=20, pady=10)

        begin_adjust = tk.Frame(center_frame, bg="lightgray")
        begin_adjust.pack(side=tk.LEFT, padx=3)
        tk.Button(
            begin_adjust,
            text="▲",
            width=3,
            command=lambda: self.adjust_time("begin", +0.01),
        ).pack()
        tk.Button(
            begin_adjust,
            text="▼",
            width=3,
            command=lambda: self.adjust_time("begin", -0.01),
        ).pack()

        tk.Button(
            center_frame,
            text="Set",
            font=("Arial", 9, "bold"),
            bg="blue",
            fg="white",
            width=4,
            height=2,
            command=lambda: self.set_time_from_playhead("begin"),
        ).pack(side=tk.LEFT, padx=2)

        begin_frame = tk.Frame(center_frame, bg="lightgray")
        begin_frame.pack(side=tk.LEFT, padx=3)
        tk.Label(begin_frame, text="Begin", bg="lightgray", font=("Arial", 9)).pack()
        self.begin_entry = tk.Entry(
            begin_frame, width=11, font=("Arial", 10), justify=tk.CENTER
        )
        self.begin_entry.pack()
        self.begin_entry.bind(
            "<Return>", lambda _e: self.update_time_from_entry("begin")
        )

        end_frame = tk.Frame(center_frame, bg="lightgray")
        end_frame.pack(side=tk.LEFT, padx=3)
        tk.Label(end_frame, text="End", bg="lightgray", font=("Arial", 9)).pack()
        self.end_entry = tk.Entry(
            end_frame, width=11, font=("Arial", 10), justify=tk.CENTER
        )
        self.end_entry.pack()
        self.end_entry.bind("<Return>", lambda _e: self.update_time_from_entry("end"))

        tk.Button(
            center_frame,
            text="Set",
            font=("Arial", 9, "bold"),
            bg="blue",
            fg="white",
            width=4,
            height=2,
            command=lambda: self.set_time_from_playhead("end"),
        ).pack(side=tk.LEFT, padx=2)

        end_adjust = tk.Frame(center_frame, bg="lightgray")
        end_adjust.pack(side=tk.LEFT, padx=3)
        tk.Button(
            end_adjust,
            text="▲",
            width=3,
            command=lambda: self.adjust_time("end", +0.01),
        ).pack()
        tk.Button(
            end_adjust,
            text="▼",
            width=3,
            command=lambda: self.adjust_time("end", -0.01),
        ).pack()

        # Right: zoom (vertical)
        right_frame = tk.Frame(control_frame, bg="lightgray")
        right_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        tk.Button(
            right_frame,
            text="🔍+",
            font=("Arial", 11),
            width=5,
            command=lambda: self.zoom_waveform(1.5),
            relief=tk.RAISED,
            borderwidth=3,
            height=2,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            right_frame,
            text="🔍−",
            font=("Arial", 11),
            width=5,
            command=lambda: self.zoom_waveform(0.67),
            relief=tk.RAISED,
            borderwidth=3,
            height=2,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            right_frame,
            text="⬜",
            font=("Arial", 11),
            width=5,
            command=lambda: self.zoom_waveform(0),
            relief=tk.RAISED,
            borderwidth=3,
            height=2,
        ).pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def refresh_all(self) -> None:
        self.refresh_table()
        self._update_current_sentence_button()
        self.refresh_time_entries()

    def refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for s in self.sentences:
            begin_str = format_time(s.begin)
            end_str = format_time(s.end)
            confirm_str = "✓" if s.confirmed else "○"
            self.tree.insert(
                "",
                tk.END,
                values=(f"Sentence {s.id}", begin_str, end_str, s.text, confirm_str),
            )

    def refresh_time_entries(self) -> None:
        if not self.sentences or self.begin_entry is None or self.end_entry is None:
            return
        idx = max(0, min(self.current_index, len(self.sentences) - 1))
        s = self.sentences[idx]
        self.begin_entry.delete(0, tk.END)
        self.begin_entry.insert(0, format_time(s.begin))
        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(0, format_time(s.end))

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    def _on_click(self, _event) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if 0 <= idx < len(self.sentences):
            self.current_index = idx
            self.refresh_all()
            # Nếu câu có begin => nhảy waveform tới đó
            s = self.sentences[idx]
            if s.begin is not None:
                self.waveform_panel.jump_to_time(s.begin)

    def _on_double_click(self, event) -> None:
        self._on_click(event)
        self.play_current_sentence()

    # ------------------------------------------------------------------ #
    # Navigation & playback
    # ------------------------------------------------------------------ #

    def _update_current_sentence_button(self) -> None:
        if not self.sentences or self.current_sentence_btn is None:
            return
        idx = max(0, min(self.current_index, len(self.sentences) - 1))
        s = self.sentences[idx]
        self.current_sentence_btn.config(text=f"Sentence {s.id}")

    def play_current_sentence(self) -> None:
        """
        Play current sentence's [begin, end] using AudioWaveformPanel.
        """
        if not self.sentences:
            return
        idx = max(0, min(self.current_index, len(self.sentences) - 1))
        s = self.sentences[idx]

        if s.begin is None or s.end is None or s.end <= s.begin:
            messagebox.showwarning(
                "No timing",
                "This sentence does not have valid Begin/End times yet.\n"
                "Please set them in the Setup tab.",
            )
            return

        self.waveform_panel.play_range(s.begin, s.end, loop=self.is_looping)

    def toggle_pause(self) -> None:
        """
        Toggle pause/resume via waveform panel (just stop/start not implemented fully).
        Tạm thời: nếu đang play thì stop, nếu đang stop thì play window.
        """
        if self.waveform_panel.is_playing:
            self.waveform_panel.stop_playback()
            setattr(self.owner, "is_playing", False)
        else:
            # play current sentence if possible
            self.play_current_sentence()
            setattr(self.owner, "is_playing", True)

    def toggle_loop(self) -> None:
        self.is_looping = not self.is_looping
        if self.loop_btn is not None:
            self.loop_btn.config(bg="yellow" if self.is_looping else "lightgreen")
        print("Loop mode (Setup):", "ON" if self.is_looping else "OFF")

    def previous_sentence(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.refresh_all()
            s = self.sentences[self.current_index]
            if s.begin is not None:
                self.waveform_panel.jump_to_time(s.begin)

    def next_sentence(self) -> None:
        if self.current_index < len(self.sentences) - 1:
            self.current_index += 1
            self.refresh_all()
            s = self.sentences[self.current_index]
            if s.begin is not None:
                self.waveform_panel.jump_to_time(s.begin)

    # ------------------------------------------------------------------ #
    # Time editing
    # ------------------------------------------------------------------ #

    def update_time_from_entry(self, field: str) -> None:
        if not self.sentences:
            return
        idx = max(0, min(self.current_index, len(self.sentences) - 1))
        s = self.sentences[idx]

        if field == "begin":
            if self.begin_entry is None:
                return
            val_str = self.begin_entry.get()
        else:
            if self.end_entry is None:
                return
            val_str = self.end_entry.get()

        new_seconds = parse_time(val_str)
        if new_seconds is None:
            messagebox.showwarning(
                "Invalid time",
                "Please enter time in format mm:ss.mmm (e.g. 00:03.650).",
            )
            return

        if field == "begin":
            s.begin = max(0.0, new_seconds)
        else:
            s.end = max(0.0, new_seconds)

        s.confirmed = False
        self.refresh_table()
        self.refresh_time_entries()

    def adjust_time(self, field: str, delta: float) -> None:
        if not self.sentences:
            return
        idx = max(0, min(self.current_index, len(self.sentences) - 1))
        s = self.sentences[idx]

        if field == "begin":
            if s.begin is None:
                s.begin = 0.0
            s.begin = max(0.0, s.begin + delta)
        else:
            if s.end is None:
                s.end = 0.0
            s.end = max(0.0, s.end + delta)

        s.confirmed = False
        self.refresh_table()
        self.refresh_time_entries()

    def set_time_from_playhead(self, field: str) -> None:
        """
        Placeholder: chưa có playhead chính xác (tương lai có thể thêm).
        """
        messagebox.showinfo(
            "Set Time",
            f"In a future version this would set {field.upper()} "
            f"from the current playhead position.",
        )

    # ------------------------------------------------------------------ #
    # Waveform zoom
    # ------------------------------------------------------------------ #

    def zoom_waveform(self, factor: float) -> None:
        self.waveform_panel.zoom_y(factor)
