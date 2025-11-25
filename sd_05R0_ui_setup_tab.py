"""
sd_05R0_ui_setup_tab.py

UI for the Setup tab of the Shadowing English app (R0).

This module defines a SetupTab class which:

- Renders the Setup table (No, Begin, End, Content, Confirm).
- Provides Begin/End input fields and ▲▼ adjust buttons.
- Integrates with a WaveformView for highlighting the current sentence.
- Relies on an external "owner" object for:
    - sentences: list[Sentence]
    - current_sentence: int
    - playback_speed: float
    - is_looping: bool
    - waveform_zoom: float

The owner is usually the main application class (e.g., ShadowingEnglishApp),
but we do not import it here to avoid circular imports.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from sd_02R0_models import Sentence, format_time, parse_time, renumber_sentences
from sd_04R0_audio_waveform import WaveformView


class SetupTab:
    """
    Encapsulates all UI and behavior of the Setup tab.

    It does NOT own the data; instead it reads/writes:
    - owner.sentences       (list[Sentence])
    - owner.current_sentence (int)
    - owner.waveform_zoom   (float)
    - owner.playback_speed  (float)
    - owner.is_looping      (bool)

    Parameters
    ----------
    parent : tk.Frame
        Parent container into which this Setup tab will place its frame.
    owner : Any
        An object that exposes at least attributes:
            - sentences: list[Sentence]
            - current_sentence: int
            - waveform_zoom: float
    """

    def __init__(self, parent: tk.Frame, owner: Any) -> None:
        self.owner = owner

        # Outer frame that the main app can pack/place
        self.frame = tk.Frame(parent)

        # Table
        self.tree: ttk.Treeview
        self._create_table_area()

        # Control bar (navigation + begin/end editing)
        self.begin_entry: Optional[tk.Entry] = None
        self.end_entry: Optional[tk.Entry] = None
        self.current_sentence_btn: Optional[tk.Button] = None
        self.loop_btn: Optional[tk.Button] = None
        self._create_control_bar()

        # Waveform
        self.waveform_view = WaveformView(self.frame)
        self.waveform_view.frame.pack(fill=tk.BOTH, padx=5, pady=5)

        # Initial refresh
        self.refresh_all()

    # ------------------------------------------------------------------ #
    # Internal helpers to access owner's state
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
    def waveform_zoom(self) -> float:
        return float(getattr(self.owner, "waveform_zoom", 1.0))

    @waveform_zoom.setter
    def waveform_zoom(self, value: float) -> None:
        setattr(self.owner, "waveform_zoom", float(value))

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

        # Center: Begin/End editing + small Δt buttons
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

        # Right: waveform zoom
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
    # Public API for the main app
    # ------------------------------------------------------------------ #

    def refresh_all(self) -> None:
        """
        Refresh table, current sentence label, begin/end entries, and waveform.
        """
        self.refresh_table()
        self._update_current_sentence_button()
        self.refresh_time_entries()
        self.refresh_waveform()

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
        if not self.sentences:
            return
        idx = max(0, min(self.current_index, len(self.sentences) - 1))
        s = self.sentences[idx]
        if self.begin_entry is not None:
            self.begin_entry.delete(0, tk.END)
            self.begin_entry.insert(0, format_time(s.begin))
        if self.end_entry is not None:
            self.end_entry.delete(0, tk.END)
            self.end_entry.insert(0, format_time(s.end))

    def refresh_waveform(self) -> None:
        self.waveform_view.set_zoom(self.waveform_zoom)
        self.waveform_view.redraw(self.sentences, self.current_index)

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #

    def _on_click(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        idx = self.tree.index(selection[0])
        if 0 <= idx < len(self.sentences):
            self.current_index = idx
            self.refresh_all()

    def _on_double_click(self, event: tk.Event) -> None:
        self._on_click(event)
        self.play_current_sentence()

    # ------------------------------------------------------------------ #
    # Sentence navigation & playback (placeholder)
    # ------------------------------------------------------------------ #

    def _update_current_sentence_button(self) -> None:
        if not self.sentences or self.current_sentence_btn is None:
            return
        idx = max(0, min(self.current_index, len(self.sentences) - 1))
        s = self.sentences[idx]
        self.current_sentence_btn.config(text=f"Sentence {s.id}")

    def play_current_sentence(self) -> None:
        """
        Placeholder: in a future version this should call an AudioController.
        For now we only show an info messagebox if timing is valid.
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

        duration = s.end - s.begin
        messagebox.showinfo(
            "Play (Setup)",
            f"Playing Sentence {s.id}\n"
            f"Duration: {duration:.2f}s at {self.playback_speed}x speed\n\n"
            f"{s.text[:60]}...",
        )

    def toggle_pause(self) -> None:
        """
        Placeholder pause toggle, only prints to stdout.
        Real audio should be handled by an AudioController.
        """
        # Flip a flag on owner if it exists
        cur = bool(getattr(self.owner, "is_playing", False))
        setattr(self.owner, "is_playing", not cur)
        print("Playback", "Playing" if not cur else "Paused (Setup)")

    def toggle_loop(self) -> None:
        self.is_looping = not self.is_looping
        if self.loop_btn is not None:
            self.loop_btn.config(bg="yellow" if self.is_looping else "lightgreen")
        print("Loop mode (Setup):", "ON" if self.is_looping else "OFF")

    def previous_sentence(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.refresh_all()

    def next_sentence(self) -> None:
        if self.current_index < len(self.sentences) - 1:
            self.current_index += 1
            self.refresh_all()

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
        self.refresh_waveform()

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
        self.refresh_waveform()

    def set_time_from_playhead(self, field: str) -> None:
        """
        Placeholder: no real playhead yet. Shows an info box.
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
        """
        Update the owner's waveform_zoom and redraw the waveform.
        factor = 0 => reset to 1.0
        """
        if factor == 0:
            self.waveform_zoom = 1.0
        else:
            self.waveform_zoom *= factor
        self.refresh_waveform()
