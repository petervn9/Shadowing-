"""
sd_01R0_main.py

Main Tkinter application for the Shadowing English learning app (R0).

- Two tabs: Setup & Practice (implemented in this single file for now).
- Manual timing: user enters Begin/End times in Setup tab.
- JSON I/O & sentence models are delegated to sd_02R0_models / sd_03R0_lesson_io.
"""

from __future__ import annotations

import os
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from sd_02R0_models import (
    Sentence,
    DictionaryEntry,
    LessonData,
    format_time,
    parse_time,
    renumber_sentences,
)
from sd_03R0_lesson_io import (
    load_lesson_from_json,
    save_lesson_to_json,
    create_sentences_from_text,
    find_matching_json_for_audio,
)


class ShadowingEnglishApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Shadowing English Learning App (R0)")
        self.root.geometry("1400x900")

        # Lesson state
        self.sentences: list[Sentence] = []
        self.dictionary: list[DictionaryEntry] = []
        self.current_sentence: int = 0
        self.current_json_file: str | None = None
        self.audio_path: str | None = None
        self.text_path: str | None = None

        # Playback state (audio is still placeholder here)
        self.is_playing: bool = False
        self.is_looping: bool = False
        self.playback_speed: float = 1.0
        self.waveform_zoom: float = 1.0

        # UI references (will be set later)
        self.setup_frame: tk.Frame | None = None
        self.practice_frame: tk.Frame | None = None
        self.content_frame: tk.Frame | None = None
        self.setup_tree: ttk.Treeview | None = None
        self.practice_tree: ttk.Treeview | None = None
        self.dict_tree: ttk.Treeview | None = None
        self.waveform_canvas: tk.Canvas | None = None
        self.begin_entry: tk.Entry | None = None
        self.end_entry: tk.Entry | None = None
        self.setup_current_btn: tk.Button | None = None
        self.practice_current_btn: tk.Button | None = None
        self.setup_loop_btn: tk.Button | None = None
        self.practice_loop_btn: tk.Button | None = None
        self.speed_buttons: dict[float, tk.Button] = {}

        # Initialize with sample data
        self._init_sample_data()

        # Create UI
        self._create_ui()

    # ------------------------------------------------------------------ #
    # Initial sample data
    # ------------------------------------------------------------------ #

    def _init_sample_data(self) -> None:
        """
        Initialize with demo sentences and dictionary, used when app starts
        with no lesson loaded.
        """
        self.sentences = [
            Sentence(
                id=1,
                begin=0.0,
                end=2.85,
                text="Good morning.",
                confirmed=True,
                practice_mode="show",
                practice_text="Good morning.",
                original_text="Good morning.",
                highlight_words=[],
            ),
            Sentence(
                id=2,
                begin=2.85,
                end=3.15,
                text="Morning, I tripped and broke the heel on this shoe.",
                confirmed=True,
                practice_mode="show",
                practice_text="Morning, I tripped and broke the heel on this shoe.",
                original_text="Gary had the same problems that many cities in the U.S.A.",
                highlight_words=["same", "many"],
            ),
            Sentence(
                id=3,
                begin=3.15,
                end=3.65,
                text="Could you fix it?",
                confirmed=False,
                practice_mode="hide",
                practice_text="Could you _____ it?",
                original_text="Could you fix it?",
                highlight_words=[],
            ),
            Sentence(
                id=4,
                begin=3.65,
                end=4.85,
                text=(
                    "And also, I'd like the sleeves on this shirt made a little shorter please."
                ),
                confirmed=False,
                practice_mode="hide",
                practice_text="_____ _____ _____ _____ _____?",
                original_text=(
                    "And also, I'd like the sleeves on this shirt made a little "
                    "shorter please."
                ),
                highlight_words=[],
            ),
            Sentence(
                id=5,
                begin=4.85,
                end=4.987,
                text=(
                    "Okay, class, before beginning the experiment, divide yourselves "
                    "into 6 groups."
                ),
                confirmed=False,
                practice_mode="hide",
                practice_text="_____________________________________.",
                original_text=(
                    "Okay, class, before beginning the experiment, divide yourselves "
                    "into 6 groups."
                ),
                highlight_words=[],
            ),
            Sentence(
                id=6,
                begin=None,
                end=None,
                text="4 or 5 students in each group please.",
                confirmed=False,
                practice_mode="hide",
                practice_text="_____ _____ _____ _____ _____ _____.",
                original_text="4 or 5 students in each group please.",
                highlight_words=[],
            ),
            Sentence(
                id=7,
                begin=None,
                end=None,
                text=(
                    "We'll be using chemicals, so everyone must put on laboratory "
                    "coats and plastic gloves."
                ),
                confirmed=False,
                practice_mode="hide",
                practice_text=(
                    "_____ _____ _____ _____ _____ _____ _____."
                ),
                original_text=(
                    "We'll be using chemicals, so everyone must put on laboratory "
                    "coats and plastic gloves."
                ),
                highlight_words=[],
            ),
        ]

        self.dictionary = [
            DictionaryEntry("near", "gần"),
            DictionaryEntry("same", "giống"),
            DictionaryEntry("many", "nhiều"),
            DictionaryEntry("lucky", "may mắn"),
            DictionaryEntry("work", "làm việc"),
            DictionaryEntry("mill", "nhà máy"),
            DictionaryEntry("southern", "phía nam"),
            DictionaryEntry("complain", "phàn nàn"),
            DictionaryEntry("single-family", "nhà riêng"),
        ]

        renumber_sentences(self.sentences)
        self.current_sentence = 0
        self.audio_path = None
        self.text_path = None
        self.current_json_file = None

    # ------------------------------------------------------------------ #
    # UI creation
    # ------------------------------------------------------------------ #

    def _create_ui(self) -> None:
        # Tabs (manual, not Notebook)
        tab_frame = tk.Frame(self.root, bg="white", relief=tk.RAISED, borderwidth=2)
        tab_frame.pack(fill=tk.X)

        self.setup_tab_btn = tk.Button(
            tab_frame,
            text="Setup",
            font=("Arial", 12, "bold"),
            width=15,
            command=lambda: self._switch_tab("setup"),
            relief=tk.SUNKEN,
            bg="white",
        )
        self.setup_tab_btn.pack(side=tk.LEFT)

        self.practice_tab_btn = tk.Button(
            tab_frame,
            text="Practice",
            font=("Arial", 12, "bold"),
            width=15,
            command=lambda: self._switch_tab("practice"),
            relief=tk.RAISED,
            bg="lightgray",
        )
        self.practice_tab_btn.pack(side=tk.LEFT)

        # Main container
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Sidebar (left)
        self._create_sidebar()

        # Content area (right)
        self.content_frame = tk.Frame(self.main_container)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create both tabs
        self._create_setup_tab()
        self._create_practice_tab()

        # Show Setup by default
        self.setup_frame.pack(fill=tk.BOTH, expand=True)

    def _create_sidebar(self) -> None:
        sidebar = tk.Frame(
            self.main_container, width=130, bg="lightgray", relief=tk.RAISED, borderwidth=2
        )
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        buttons = [
            ("Open", self._open_file),
            ("Save section", self._save_section),
            ("Save as...", self._save_as),
            ("New talk", self._new_talk),
            ("Delete", self._delete_sentence),
        ]

        for text, command in buttons:
            btn = tk.Button(
                sidebar,
                text=text,
                font=("Arial", 10, "bold"),
                command=command,
                relief=tk.RAISED,
                borderwidth=3,
                height=2,
            )
            btn.pack(pady=5, padx=5, fill=tk.X)

    # ------------------------------------------------------------------ #
    # Setup tab
    # ------------------------------------------------------------------ #

    def _create_setup_tab(self) -> None:
        self.setup_frame = tk.Frame(self.content_frame)

        table_frame = tk.Frame(self.setup_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        v_scrollbar = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        h_scrollbar = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        columns = ("No", "Begin", "End", "Content", "Confirm")
        self.setup_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
        )

        v_scrollbar.config(command=self.setup_tree.yview)
        h_scrollbar.config(command=self.setup_tree.xview)

        self.setup_tree.heading("No", text="No")
        self.setup_tree.heading("Begin", text="Begin")
        self.setup_tree.heading("End", text="End")
        self.setup_tree.heading("Content", text="Content")
        self.setup_tree.heading("Confirm", text="Confirm")

        self.setup_tree.column("No", width=80, anchor=tk.CENTER)
        self.setup_tree.column("Begin", width=100, anchor=tk.CENTER)
        self.setup_tree.column("End", width=100, anchor=tk.CENTER)
        self.setup_tree.column("Content", width=700)
        self.setup_tree.column("Confirm", width=80, anchor=tk.CENTER)

        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.setup_tree.pack(fill=tk.BOTH, expand=True)

        self.setup_tree.bind(
            "<ButtonRelease-1>", lambda e: self._on_sentence_click("setup")
        )
        self.setup_tree.bind(
            "<Double-1>", lambda e: self._on_sentence_double_click("setup")
        )

        self._create_control_bar(self.setup_frame, "setup")
        self._create_waveform(self.setup_frame)
        self._refresh_setup_table()

    # ------------------------------------------------------------------ #
    # Practice tab
    # ------------------------------------------------------------------ #

    def _create_practice_tab(self) -> None:
        self.practice_frame = tk.Frame(self.content_frame)

        practice_container = tk.Frame(self.practice_frame)
        practice_container.pack(fill=tk.BOTH, expand=True)

        # Left: Practice table
        table_frame = tk.Frame(practice_container)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        v_scrollbar = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        h_scrollbar = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        columns = ("No", "Content", "Hide", "Show")
        self.practice_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
        )

        v_scrollbar.config(command=self.practice_tree.yview)
        h_scrollbar.config(command=self.practice_tree.xview)

        self.practice_tree.heading("No", text="No")
        self.practice_tree.heading("Content", text="Content")
        self.practice_tree.heading("Hide", text="Hide")
        self.practice_tree.heading("Show", text="Show")

        self.practice_tree.column("No", width=80, anchor=tk.CENTER)
        self.practice_tree.column("Content", width=600)
        self.practice_tree.column("Hide", width=80, anchor=tk.CENTER)
        self.practice_tree.column("Show", width=80, anchor=tk.CENTER)

        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.practice_tree.pack(fill=tk.BOTH, expand=True)

        self.practice_tree.bind(
            "<ButtonRelease-1>", lambda e: self._on_sentence_click("practice")
        )
        self.practice_tree.bind(
            "<Double-1>", lambda e: self._on_sentence_double_click("practice")
        )

        # Dictionary panel
        self._create_dictionary(practice_container)

        # Control bar + waveform
        self._create_control_bar(self.practice_frame, "practice")
        self._create_waveform(self.practice_frame)
        self._refresh_practice_table()

    # ------------------------------------------------------------------ #
    # Dictionary panel
    # ------------------------------------------------------------------ #

    def _create_dictionary(self, parent: tk.Frame) -> None:
        dict_frame = tk.Frame(parent, width=380, relief=tk.RAISED, borderwidth=2)
        dict_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        dict_frame.pack_propagate(False)

        title = tk.Label(
            dict_frame, text="Dictionary", font=("Arial", 12, "bold"), bg="lightgray"
        )
        title.pack(fill=tk.X, pady=5)

        scrollbar = tk.Scrollbar(dict_frame, orient=tk.VERTICAL)

        columns = ("No", "Word", "Meaning")
        self.dict_tree = ttk.Treeview(
            dict_frame,
            columns=columns,
            show="headings",
            yscrollcommand=scrollbar.set,
        )

        scrollbar.config(command=self.dict_tree.yview)

        self.dict_tree.heading("No", text="No.")
        self.dict_tree.heading("Word", text="Word")
        self.dict_tree.heading("Meaning", text="Meaning (VI)")

        self.dict_tree.column("No", width=50, anchor=tk.CENTER)
        self.dict_tree.column("Word", width=130)
        self.dict_tree.column("Meaning", width=170)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.dict_tree.pack(fill=tk.BOTH, expand=True)

        self._refresh_dictionary()

    # ------------------------------------------------------------------ #
    # Control bars
    # ------------------------------------------------------------------ #

    def _create_control_bar(self, parent: tk.Frame, tab_type: str) -> None:
        control_frame = tk.Frame(
            parent, bg="lightgray", relief=tk.RAISED, borderwidth=2, height=90
        )
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        control_frame.pack_propagate(False)

        # Left controls
        left_frame = tk.Frame(control_frame, bg="lightgray")
        left_frame.pack(side=tk.LEFT, padx=10, pady=10)

        prev_btn = tk.Button(
            left_frame,
            text="◄◄",
            font=("Arial", 14, "bold"),
            width=4,
            command=self._previous_sentence,
            bg="lightgreen",
            relief=tk.RAISED,
            borderwidth=3,
        )
        prev_btn.pack(side=tk.LEFT, padx=2)

        if tab_type == "setup":
            self.setup_current_btn = tk.Button(
                left_frame,
                text="Sentence 1",
                font=("Arial", 14, "bold"),
                width=12,
                command=self._play_current_sentence,
                bg="green",
                fg="white",
                relief=tk.RAISED,
                borderwidth=3,
            )
            self.setup_current_btn.pack(side=tk.LEFT, padx=2)
        else:
            self.practice_current_btn = tk.Button(
                left_frame,
                text="Sentence 1",
                font=("Arial", 14, "bold"),
                width=12,
                command=self._play_current_sentence,
                bg="green",
                fg="white",
                relief=tk.RAISED,
                borderwidth=3,
            )
            self.practice_current_btn.pack(side=tk.LEFT, padx=2)

        pause_btn = tk.Button(
            left_frame,
            text="❚❚",
            font=("Arial", 14, "bold"),
            width=4,
            command=self._toggle_pause,
            bg="lightgreen",
            relief=tk.RAISED,
            borderwidth=3,
        )
        pause_btn.pack(side=tk.LEFT, padx=2)

        next_btn = tk.Button(
            left_frame,
            text="►►",
            font=("Arial", 14, "bold"),
            width=4,
            command=self._next_sentence,
            bg="lightgreen",
            relief=tk.RAISED,
            borderwidth=3,
        )
        next_btn.pack(side=tk.LEFT, padx=2)

        if tab_type == "setup":
            self.setup_loop_btn = tk.Button(
                left_frame,
                text="🔁",
                font=("Arial", 12),
                width=4,
                command=self._toggle_loop,
                bg="lightgreen",
                relief=tk.RAISED,
                borderwidth=3,
            )
            self.setup_loop_btn.pack(side=tk.LEFT, padx=2)
        else:
            self.practice_loop_btn = tk.Button(
                left_frame,
                text="🔁",
                font=("Arial", 12),
                width=4,
                command=self._toggle_loop,
                bg="lightgreen",
                relief=tk.RAISED,
                borderwidth=3,
            )
            self.practice_loop_btn.pack(side=tk.LEFT, padx=2)

        # Center block
        if tab_type == "setup":
            center_frame = tk.Frame(control_frame, bg="lightgray")
            center_frame.pack(side=tk.LEFT, padx=20, pady=10)

            # Begin adjust ▲▼
            begin_adjust_frame = tk.Frame(center_frame, bg="lightgray")
            begin_adjust_frame.pack(side=tk.LEFT, padx=3)

            tk.Button(
                begin_adjust_frame,
                text="▲",
                width=3,
                command=lambda: self._adjust_time("begin", 0.01),
            ).pack()
            tk.Button(
                begin_adjust_frame,
                text="▼",
                width=3,
                command=lambda: self._adjust_time("begin", -0.01),
            ).pack()

            tk.Button(
                center_frame,
                text="Set",
                font=("Arial", 9, "bold"),
                bg="blue",
                fg="white",
                width=4,
                height=2,
                command=lambda: self._set_time_from_playhead("begin"),
            ).pack(side=tk.LEFT, padx=2)

            begin_frame = tk.Frame(center_frame, bg="lightgray")
            begin_frame.pack(side=tk.LEFT, padx=3)
            tk.Label(begin_frame, text="Begin", bg="lightgray", font=("Arial", 9)).pack()
            self.begin_entry = tk.Entry(
                begin_frame, width=11, font=("Arial", 10), justify=tk.CENTER
            )
            self.begin_entry.pack()
            self.begin_entry.bind(
                "<Return>", lambda e: self._update_time_from_entry("begin")
            )

            end_frame = tk.Frame(center_frame, bg="lightgray")
            end_frame.pack(side=tk.LEFT, padx=3)
            tk.Label(end_frame, text="End", bg="lightgray", font=("Arial", 9)).pack()
            self.end_entry = tk.Entry(
                end_frame, width=11, font=("Arial", 10), justify=tk.CENTER
            )
            self.end_entry.pack()
            self.end_entry.bind(
                "<Return>", lambda e: self._update_time_from_entry("end")
            )

            tk.Button(
                center_frame,
                text="Set",
                font=("Arial", 9, "bold"),
                bg="blue",
                fg="white",
                width=4,
                height=2,
                command=lambda: self._set_time_from_playhead("end"),
            ).pack(side=tk.LEFT, padx=2)

            end_adjust_frame = tk.Frame(center_frame, bg="lightgray")
            end_adjust_frame.pack(side=tk.LEFT, padx=3)

            tk.Button(
                end_adjust_frame,
                text="▲",
                width=3,
                command=lambda: self._adjust_time("end", 0.01),
            ).pack()
            tk.Button(
                end_adjust_frame,
                text="▼",
                width=3,
                command=lambda: self._adjust_time("end", -0.01),
            ).pack()

        if tab_type == "practice":
            speed_frame = tk.Frame(
                control_frame, bg="white", relief=tk.RAISED, borderwidth=2
            )
            speed_frame.pack(side=tk.LEFT, padx=20, pady=15)

            speeds = [0.5, 0.75, 1.0, 1.2, 1.5]
            self.speed_buttons = {}

            for speed in speeds:
                btn = tk.Button(
                    speed_frame,
                    text=f"{speed}x",
                    font=("Arial", 10),
                    width=6,
                    command=lambda s=speed: self._set_speed(s),
                    relief=tk.RAISED,
                    borderwidth=2,
                    height=2,
                )
                btn.pack(side=tk.LEFT, padx=1)
                self.speed_buttons[speed] = btn
                if speed == 1.0:
                    btn.config(bg="yellow", font=("Arial", 10, "bold"))

        # Right: zoom
        right_frame = tk.Frame(control_frame, bg="lightgray")
        right_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        tk.Button(
            right_frame,
            text="🔍+",
            font=("Arial", 11),
            width=5,
            command=lambda: self._zoom_waveform(1.5),
            relief=tk.RAISED,
            borderwidth=3,
            height=2,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            right_frame,
            text="🔍−",
            font=("Arial", 11),
            width=5,
            command=lambda: self._zoom_waveform(0.67),
            relief=tk.RAISED,
            borderwidth=3,
            height=2,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            right_frame,
            text="⬜",
            font=("Arial", 11),
            width=5,
            command=lambda: self._zoom_waveform(0),
            relief=tk.RAISED,
            borderwidth=3,
            height=2,
        ).pack(side=tk.LEFT, padx=2)

    # ------------------------------------------------------------------ #
    # Waveform (fake, for now)
    # ------------------------------------------------------------------ #

    def _create_waveform(self, parent: tk.Frame) -> None:
        waveform_frame = tk.Frame(
            parent, bg="black", height=220, relief=tk.SUNKEN, borderwidth=2
        )
        waveform_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        waveform_frame.pack_propagate(False)

        self.waveform_canvas = tk.Canvas(
            waveform_frame, bg="black", highlightthickness=0
        )
        self.waveform_canvas.pack(fill=tk.BOTH, expand=True)

        self.root.after(100, self._draw_waveform)

    def _draw_waveform(self) -> None:
        if self.waveform_canvas is None:
            return

        canvas = self.waveform_canvas
        canvas.delete("all")
        width = canvas.winfo_width() or 1200
        height = canvas.winfo_height() or 200

        # Highlight current sentence region (if any timing)
        if 0 <= self.current_sentence < len(self.sentences):
            s = self.sentences[self.current_sentence]
            if s.begin is not None and s.end is not None:
                total_duration = 12.0 / max(self.waveform_zoom, 0.01)
                start_x = (s.begin / total_duration) * width
                end_x = (s.end / total_duration) * width
                canvas.create_rectangle(
                    start_x,
                    0,
                    end_x,
                    height,
                    fill="blue",
                    stipple="gray50",
                )

        # Fake waveform
        import random as _random

        points = []
        for i in range(0, width, 10):
            y = height / 2 + _random.randint(-80, 80)
            points.extend([i, y])

        if len(points) > 2:
            canvas.create_line(points, fill="lime", width=2, smooth=True)

        time_labels = ["0:00", "0:03", "0:06", "0:09", "0:12"]
        for i, label in enumerate(time_labels):
            x = (i / (len(time_labels) - 1)) * width
            canvas.create_text(
                x,
                height - 10,
                text=label,
                fill="white",
                font=("Arial", 9),
            )

    # ------------------------------------------------------------------ #
    # Refresh tables
    # ------------------------------------------------------------------ #

    def _refresh_setup_table(self) -> None:
        if self.setup_tree is None:
            return
        self.setup_tree.delete(*self.setup_tree.get_children())

        for s in self.sentences:
            begin_str = format_time(s.begin)
            end_str = format_time(s.end)
            confirm_str = "✓" if s.confirmed else "○"
            self.setup_tree.insert(
                "",
                tk.END,
                values=(f"Sentence {s.id}", begin_str, end_str, s.text, confirm_str),
            )

        if self.sentences and self.setup_current_btn is not None:
            self.setup_current_btn.config(
                text=f"Sentence {self.sentences[self.current_sentence].id}"
            )
            if self.begin_entry is not None:
                self._update_time_entries()

    def _refresh_practice_table(self) -> None:
        if self.practice_tree is None:
            return
        self.practice_tree.delete(*self.practice_tree.get_children())

        for s in self.sentences:
            if s.practice_mode == "hide":
                content = s.practice_text
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

        if self.sentences and self.practice_current_btn is not None:
            self.practice_current_btn.config(
                text=f"Sentence {self.sentences[self.current_sentence].id}"
            )

    def _refresh_dictionary(self) -> None:
        if self.dict_tree is None:
            return
        self.dict_tree.delete(*self.dict_tree.get_children())

        for i, entry in enumerate(self.dictionary, start=1):
            self.dict_tree.insert(
                "",
                tk.END,
                values=(i, entry.word, entry.meaning_vi),
            )

    # ------------------------------------------------------------------ #
    # Time helpers connected to UI
    # ------------------------------------------------------------------ #

    def _update_time_entries(self) -> None:
        if not (0 <= self.current_sentence < len(self.sentences)):
            return
        s = self.sentences[self.current_sentence]
        if self.begin_entry is not None:
            self.begin_entry.delete(0, tk.END)
            self.begin_entry.insert(0, format_time(s.begin))
        if self.end_entry is not None:
            self.end_entry.delete(0, tk.END)
            self.end_entry.insert(0, format_time(s.end))

    def _update_time_from_entry(self, field: str) -> None:
        if not (0 <= self.current_sentence < len(self.sentences)):
            return
        s = self.sentences[self.current_sentence]
        if field == "begin":
            if self.begin_entry is None:
                return
            time_val = parse_time(self.begin_entry.get())
        else:
            if self.end_entry is None:
                return
            time_val = parse_time(self.end_entry.get())

        if time_val is not None:
            if field == "begin":
                s.begin = max(0.0, time_val)
            else:
                s.end = max(0.0, time_val)
            s.confirmed = False
            self._refresh_setup_table()
            self._draw_waveform()
        else:
            messagebox.showwarning(
                "Invalid time",
                "Please enter time in format mm:ss.mmm (e.g. 00:03.650).",
            )

    def _set_time_from_playhead(self, field: str) -> None:
        # Placeholder: no real audio backend yet
        messagebox.showinfo(
            "Set Time",
            f"In a future version this would set {field.upper()} "
            f"from the current playhead position.",
        )

    # ------------------------------------------------------------------ #
    # Tab switching
    # ------------------------------------------------------------------ #

    def _switch_tab(self, tab_name: str) -> None:
        if tab_name == "setup":
            self.setup_tab_btn.config(relief=tk.SUNKEN, bg="white")
            self.practice_tab_btn.config(relief=tk.RAISED, bg="lightgray")
            self.practice_frame.pack_forget()
            self.setup_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_setup_table()
        else:
            self.practice_tab_btn.config(relief=tk.SUNKEN, bg="white")
            self.setup_tab_btn.config(relief=tk.RAISED, bg="lightgray")
            self.setup_frame.pack_forget()
            self.practice_frame.pack(fill=tk.BOTH, expand=True)
            self._refresh_practice_table()

        self.root.after(100, self._draw_waveform)

    # ------------------------------------------------------------------ #
    # Sentence selection & playback (placeholder)
    # ------------------------------------------------------------------ #

    def _on_sentence_click(self, tab_type: str) -> None:
        if tab_type == "setup" and self.setup_tree is not None:
            sel = self.setup_tree.selection()
            if sel:
                index = self.setup_tree.index(sel[0])
                self.current_sentence = index
                self._refresh_setup_table()
        elif tab_type == "practice" and self.practice_tree is not None:
            sel = self.practice_tree.selection()
            if sel:
                index = self.practice_tree.index(sel[0])
                self.current_sentence = index
                self._refresh_practice_table()
        self._draw_waveform()

    def _on_sentence_double_click(self, tab_type: str) -> None:
        self._on_sentence_click(tab_type)
        self._play_current_sentence()

    def _play_current_sentence(self) -> None:
        if not (0 <= self.current_sentence < len(self.sentences)):
            return
        s = self.sentences[self.current_sentence]
        if s.begin is not None and s.end is not None and s.end > s.begin:
            self.is_playing = True
            duration = s.end - s.begin
            messagebox.showinfo(
                "Play",
                (
                    f"Playing Sentence {s.id}\n"
                    f"Duration: {duration:.2f}s at {self.playback_speed}x speed\n\n"
                    f"{s.text[:60]}..."
                ),
            )
        else:
            messagebox.showwarning(
                "No timing",
                "This sentence does not have valid Begin/End times yet.\n"
                "Please set them in the Setup tab.",
            )

    def _toggle_pause(self) -> None:
        self.is_playing = not self.is_playing
        print("Playback", "Playing" if self.is_playing else "Paused")

    def _toggle_loop(self) -> None:
        self.is_looping = not self.is_looping
        bg_color = "yellow" if self.is_looping else "lightgreen"

        if self.setup_loop_btn is not None:
            self.setup_loop_btn.config(bg=bg_color)
        if self.practice_loop_btn is not None:
            self.practice_loop_btn.config(bg=bg_color)

        print("Loop mode:", "ON" if self.is_looping else "OFF")

    def _previous_sentence(self) -> None:
        if self.current_sentence > 0:
            self.current_sentence -= 1
            self._refresh_setup_table()
            self._refresh_practice_table()
            self._draw_waveform()

    def _next_sentence(self) -> None:
        if self.current_sentence < len(self.sentences) - 1:
            self.current_sentence += 1
            self._refresh_setup_table()
            self._refresh_practice_table()
            self._draw_waveform()

    def _adjust_time(self, field: str, delta: float) -> None:
        if not (0 <= self.current_sentence < len(self.sentences)):
            return
        s = self.sentences[self.current_sentence]
        if field == "begin":
            if s.begin is None:
                s.begin = 0.0
            s.begin = max(0.0, s.begin + delta)
        else:
            if s.end is None:
                s.end = 0.0
            s.end = max(0.0, s.end + delta)
        s.confirmed = False
        self._refresh_setup_table()
        self._draw_waveform()

    def _set_speed(self, speed: float) -> None:
        self.playback_speed = speed
        for s, btn in self.speed_buttons.items():
            if s == speed:
                btn.config(bg="yellow", font=("Arial", 10, "bold"))
            else:
                btn.config(bg="white", font=("Arial", 10))
        print(f"Playback speed set to {speed}x")

    def _zoom_waveform(self, factor: float) -> None:
        if factor == 0:
            self.waveform_zoom = 1.0
            print("Waveform: fit to window")
        else:
            self.waveform_zoom *= factor
            print(f"Waveform zoom = {self.waveform_zoom:.2f}x")
        self._draw_waveform()

    # ------------------------------------------------------------------ #
    # OPEN / SAVE (using lesson_io)
    # ------------------------------------------------------------------ #

    def _open_file(self) -> None:
        """
        Open:
        - Yes  => open existing JSON lesson.
        - No   => create new lesson from AUDIO + TEXT (manual timing).
        """
        choice = messagebox.askyesnocancel(
            "Open",
            "What do you want to open?\n\n"
            "Yes  = Open existing JSON lesson\n"
            "No   = Create NEW lesson from audio + text (manual timing)\n"
            "Cancel = Do nothing",
        )
        if choice is None:
            return
        if choice:
            self._open_json_lesson()
        else:
            self._open_audio_text_lesson()

    def _open_json_lesson(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Open JSON lesson file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            lesson = load_lesson_from_json(file_path)

            self.sentences = lesson.sentences
            self.dictionary = lesson.dictionary
            self.audio_path = lesson.audio_path
            self.text_path = lesson.text_path
            self.playback_speed = lesson.play_speed
            self.current_sentence = max(
                0, min(lesson.last_selected_sentence, len(self.sentences) - 1)
            )
            self.current_json_file = file_path

            self._refresh_setup_table()
            self._refresh_practice_table()
            self._refresh_dictionary()
            self._draw_waveform()

            messagebox.showinfo(
                "Success", f"Loaded lesson from:\n{os.path.basename(file_path)}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file:\n{e}")

    def _open_audio_text_lesson(self) -> None:
        # Select audio
        audio_path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[
                (
                    "Audio files",
                    "*.mp3;*.wav;*.m4a;*.flac;*.ogg",
                ),
                ("All files", "*.*"),
            ],
        )
        if not audio_path:
            return

        # Select text
        text_path = filedialog.askopenfilename(
            title="Select text file (script)",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not text_path:
            return

        try:
            sentences = create_sentences_from_text(text_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create lesson from text:\n{e}")
            return

        self.sentences = sentences
        self.dictionary = []
        self.current_sentence = 0
        self.audio_path = audio_path
        self.text_path = text_path
        self.playback_speed = 1.0
        self.current_json_file = None

        self._refresh_setup_table()
        self._refresh_practice_table()
        self._refresh_dictionary()
        self._draw_waveform()

        # Optional: check if matching JSON exists
        json_candidate = find_matching_json_for_audio(audio_path)
        if json_candidate:
            if messagebox.askyesno(
                "Existing setup found",
                f"A JSON setup file was found:\n{os.path.basename(json_candidate)}\n\n"
                f"Do you want to load timing and dictionary from it?",
            ):
                try:
                    lesson = load_lesson_from_json(json_candidate)
                    self.sentences = lesson.sentences
                    self.dictionary = lesson.dictionary
                    self.audio_path = lesson.audio_path or audio_path
                    self.text_path = lesson.text_path or text_path
                    self.playback_speed = lesson.play_speed
                    self.current_sentence = max(
                        0,
                        min(
                            lesson.last_selected_sentence,
                            len(self.sentences) - 1,
                        ),
                    )
                    self.current_json_file = json_candidate
                    self._refresh_setup_table()
                    self._refresh_practice_table()
                    self._refresh_dictionary()
                    self._draw_waveform()
                except Exception as e:
                    messagebox.showerror(
                        "Error", f"Failed to load existing setup:\n{e}"
                    )
                    # keep the new sentences (Begin/End None)

        messagebox.showinfo(
            "New lesson",
            "A new lesson was created from AUDIO + TEXT.\n"
            "All Begin/End times are empty.\n"
            "Please set them manually in the Setup tab.",
        )

    def _save_section(self) -> None:
        if self.current_json_file:
            self._save_to_file(self.current_json_file)
        else:
            self._save_as()

    def _save_as(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Save lesson as",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if file_path:
            self._save_to_file(file_path)
            self.current_json_file = file_path

    def _save_to_file(self, file_path: str) -> None:
        try:
            lesson = LessonData(
                audio_path=self.audio_path,
                text_path=self.text_path,
                play_speed=self.playback_speed,
                last_selected_sentence=self.current_sentence,
                sentences=self.sentences,
                dictionary=self.dictionary,
            )
            save_lesson_to_json(lesson, file_path)
            messagebox.showinfo(
                "Success", f"Saved lesson to:\n{os.path.basename(file_path)}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{e}")

    # ------------------------------------------------------------------ #
    # New / Delete sentence
    # ------------------------------------------------------------------ #

    def _new_talk(self) -> None:
        new_id = len(self.sentences) + 1
        new_sentence = Sentence(
            id=new_id,
            begin=None,
            end=None,
            text="",
            confirmed=False,
            practice_mode="hide",
            practice_text="",
            original_text="",
            highlight_words=[],
        )

        insert_pos = min(self.current_sentence + 1, len(self.sentences))
        self.sentences.insert(insert_pos, new_sentence)
        renumber_sentences(self.sentences)

        self.current_sentence = insert_pos
        self._refresh_setup_table()
        self._refresh_practice_table()

        messagebox.showinfo(
            "New sentence", "A new sentence was added below the current one."
        )

    def _delete_sentence(self) -> None:
        if not self.sentences:
            messagebox.showwarning(
                "No sentences", "There are no sentences to delete."
            )
            return

        s = self.sentences[self.current_sentence]
        if not messagebox.askyesno(
            "Delete Sentence",
            f"Delete Sentence {s.id}?\n\n{s.text[:50]}...",
        ):
            return

        del self.sentences[self.current_sentence]
        if self.current_sentence >= len(self.sentences):
            self.current_sentence = max(0, len(self.sentences) - 1)
        renumber_sentences(self.sentences)

        self._refresh_setup_table()
        self._refresh_practice_table()
        self._draw_waveform()

    # ------------------------------------------------------------------ #
    # End of class
    # ------------------------------------------------------------------ #


def main() -> None:
    root = tk.Tk()
    app = ShadowingEnglishApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
