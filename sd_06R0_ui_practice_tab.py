"""
sd_06R0_ui_practice_tab.py

Practice tab UI for Shadowing English App (R0),
updated to use AudioWaveformPanel (real waveform + audio playback).

- Practice table: No, Content, Hide, Show
- Dictionary panel: Word, Meaning (VI)
- Control bar:
    + prev / current sentence (Play) / pause / next / loop
    + speed buttons (0.5x .. 1.5x) – hiện tại chỉ lưu vào owner.playback_speed
      và hiển thị, chưa thay đổi speed thực tế trong sounddevice.
- Waveform panel dưới (cùng kiểu với Setup).
- Play sentence => dùng waveform_panel.play_range(begin, end, loop=is_looping)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from sd_02R0_models import Sentence, DictionaryEntry
from sd_04R0_audio_waveform import AudioWaveformPanel
from sd_07R0_ui_common import HEADER_FONT, create_table_with_scrollbars


class PracticeTab:
    """
    Encapsulates all UI and behavior of the Practice tab.

    It reads/writes:
    - owner.sentences         (list[Sentence])
    - owner.dictionary        (list[DictionaryEntry])
    - owner.current_sentence  (int)
    - owner.audio_path        (str | None)
    - owner.waveform_panel_practice (tuỳ ý lưu)
    - owner.playback_speed    (float)
    - owner.is_looping        (bool)
    - owner.is_playing        (bool)
    """

    def __init__(self, parent: tk.Frame, owner: Any) -> None:
        self.owner = owner

        # Outer frame
        self.frame = tk.Frame(parent)

        # Main container: left (Practice table) + right (Dictionary)
        main_container = tk.Frame(self.frame)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Left side: Practice table
        self.practice_tree: ttk.Treeview
        self._create_practice_table(main_container)

        # Right side: Dictionary
        self.dict_tree: ttk.Treeview
        self._create_dictionary_panel(main_container)

        # Control bar
        self.current_sentence_btn: Optional[tk.Button] = None
        self.loop_btn: Optional[tk.Button] = None
        self.speed_buttons: Dict[float, tk.Button] = {}
        self._create_control_bar()

        # Waveform panel
        wave_container = tk.Frame(self.frame)
        wave_container.pack(fill=tk.BOTH, padx=5, pady=5, expand=True)
        self.waveform_panel = AudioWaveformPanel(wave_container)

        audio_path = getattr(self.owner, "audio_path", None)
        if audio_path:
            self.waveform_panel.set_audio_path(audio_path)

        # Initial refresh
        self.refresh_all()

    # ------------------------------------------------------------------ #
    # Owner state
    # ------------------------------------------------------------------ #

    @property
    def sentences(self) -> List[Sentence]:
        return getattr(self.owner, "sentences", [])

    @property
    def dictionary(self) -> List[DictionaryEntry]:
        return getattr(self.owner, "dictionary", [])

    @property
    def current_index(self) -> int:
        return int(getattr(self.owner, "current_sentence", 0))

    @current_index.setter
    def current_index(self, value: int) -> None:
        setattr(self.owner, "current_sentence", int(value))

    @property
    def playback_speed(self) -> float:
        return float(getattr(self.owner, "playback_speed", 1.0))

    @playback_speed.setter
    def playback_speed(self, value: float) -> None:
        setattr(self.owner, "playback_speed", float(value))

    @property
    def is_looping(self) -> bool:
        return bool(getattr(self.owner, "is_looping", False))

    @is_looping.setter
    def is_looping(self, value: bool) -> None:
        setattr(self.owner, "is_looping", bool(value))

    @property
    def is_playing(self) -> bool:
        return bool(getattr(self.owner, "is_playing", False))

    @is_playing.setter
    def is_playing(self, value: bool) -> None:
        setattr(self.owner, "is_playing", bool(value))

    # ------------------------------------------------------------------ #
    # UI creation
    # ------------------------------------------------------------------ #

    def _create_practice_table(self, parent: tk.Frame) -> None:
        table_frame = tk.Frame(parent)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("No", "Content", "Hide", "Show")
        self.practice_tree, _, _ = create_table_with_scrollbars(table_frame, columns)

        self.practice_tree.heading("No", text="No")
        self.practice_tree.heading("Content", text="Content")
        self.practice_tree.heading("Hide", text="Hide")
        self.practice_tree.heading("Show", text="Show")

        self.practice_tree.column("No", width=80, anchor=tk.CENTER)
        self.practice_tree.column("Content", width=600, anchor=tk.W)
        self.practice_tree.column("Hide", width=80, anchor=tk.CENTER)
        self.practice_tree.column("Show", width=80, anchor=tk.CENTER)

        self.practice_tree.bind("<ButtonRelease-1>", self._on_practice_click)
        self.practice_tree.bind("<Double-1>", self._on_practice_double_click)

    def _create_dictionary_panel(self, parent: tk.Frame) -> None:
        dict_frame = tk.Frame(parent, width=380, relief=tk.RAISED, borderwidth=2)
        dict_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        dict_frame.pack_propagate(False)

        title = tk.Label(
            dict_frame,
            text="Dictionary",
            font=HEADER_FONT,
            bg="#d0d0d0",
        )
        title.pack(fill=tk.X, pady=5)

        table_frame = tk.Frame(dict_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("No", "Word", "Meaning")
        self.dict_tree, _, _ = create_table_with_scrollbars(table_frame, columns)

        self.dict_tree.heading("No", text="No.")
        self.dict_tree.heading("Word", text="Word")
        self.dict_tree.heading("Meaning", text="Meaning (VI)")

        self.dict_tree.column("No", width=50, anchor=tk.CENTER)
        self.dict_tree.column("Word", width=130, anchor=tk.W)
        self.dict_tree.column("Meaning", width=170, anchor=tk.W)

    def _create_control_bar(self) -> None:
        control_frame = tk.Frame(
            self.frame, bg="#f0f0f0", relief=tk.RAISED, borderwidth=2, height=90
        )
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        control_frame.pack_propagate(False)

        # Left: navigation + loop
        left_frame = tk.Frame(control_frame, bg="#f0f0f0")
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

        # Center: speed buttons
        speed_frame = tk.Frame(
            control_frame, bg="white", relief=tk.RAISED, borderwidth=2
        )
        speed_frame.pack(side=tk.LEFT, padx=20, pady=15)

        speeds = [0.5, 0.75, 1.0, 1.2, 1.5]
        for speed in speeds:
            btn = tk.Button(
                speed_frame,
                text=f"{speed}x",
                font=("Arial", 10),
                width=6,
                command=lambda s=speed: self.set_speed(s),
                relief=tk.RAISED,
                borderwidth=2,
                height=2,
            )
            btn.pack(side=tk.LEFT, padx=1)
            self.speed_buttons[speed] = btn

        if 1.0 in self.speed_buttons:
            self.speed_buttons[1.0].config(bg="yellow", font=("Arial", 10, "bold"))

        # Right: zoom (vertical)
        right_frame = tk.Frame(control_frame, bg="#f0f0f0")
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
        self.refresh_practice_table()
        self.refresh_dictionary()
        self._update_current_sentence_button()
        self._update_speed_buttons()

    def refresh_practice_table(self) -> None:
        self.practice_tree.delete(*self.practice_tree.get_children())

        for s in self.sentences:
            if s.practice_mode == "hide":
                content = s.practice_text or s.original_text
                hide_mark = "●"
                show_mark = "○"
            else:
                content = s.original_text
                hide_mark = "○"
                show_mark = "●"

            self.practice_tree.insert(
                "",
                tk.END,
                values=(f"Sentence {s.id}", content, hide_mark, show_mark),
            )

    def refresh_dictionary(self) -> None:
        self.dict_tree.delete(*self.dict_tree.get_children())
        for i, entry in enumerate(self.dictionary, start=1):
            self.dict_tree.insert(
                "",
                tk.END,
                values=(i, entry.word, entry.meaning_vi),
            )

    # ------------------------------------------------------------------ #
    # Events – practice table
    # ------------------------------------------------------------------ #

    def _on_practice_click(self, _event) -> None:
        sel = self.practice_tree.selection()
        if not sel:
            return
        idx = self.practice_tree.index(sel[0])
        if 0 <= idx < len(self.sentences):
            self.current_index = idx
            self.refresh_all()
            s = self.sentences[idx]
            if s.begin is not None:
                self.waveform_panel.jump_to_time(s.begin)

    def _on_practice_double_click(self, event) -> None:
        self._on_practice_click(event)
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
        if self.waveform_panel.is_playing:
            self.waveform_panel.stop_playback()
            self.is_playing = False
        else:
            self.play_current_sentence()
            self.is_playing = True

    def toggle_loop(self) -> None:
        self.is_looping = not self.is_looping
        if self.loop_btn is not None:
            self.loop_btn.config(bg="yellow" if self.is_looping else "lightgreen")
        print("Loop mode (Practice):", "ON" if self.is_looping else "OFF")

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
    # Speed & zoom
    # ------------------------------------------------------------------ #

    def set_speed(self, speed: float) -> None:
        self.playback_speed = speed
        self._update_speed_buttons()
        print(f"Playback speed (Practice) set to {speed}x (logical only, not time-stretched yet).")

    def _update_speed_buttons(self) -> None:
        for s, btn in self.speed_buttons.items():
            if abs(s - self.playback_speed) < 1e-6:
                btn.config(bg="yellow", font=("Arial", 10, "bold"))
            else:
                btn.config(bg="white", font=("Arial", 10))

    def zoom_waveform(self, factor: float) -> None:
        self.waveform_panel.zoom_y(factor)
