"""Shadowing English desktop prototype.

This script provides a Tkinter-based interface with two tabs (Setup and Practice)
that mimic the behavior shown in the provided screenshots. It supports:
- Opening audio+text files or a saved JSON section
- Splitting text into sentence-like units
- Estimating begin/end timestamps aligned to the audio duration
- Editing sentences inside a table with confirm flags
- Drawing a simple waveform preview from WAV data
- Saving/loading section JSON files

Dependencies: Python standard library only (Tkinter).
Audio waveform preview works best with uncompressed .wav files.
"""
from __future__ import annotations

import json
import re
import wave
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


@dataclass
class Sentence:
    idx: int
    begin: float
    end: float
    content: str
    confirm: bool = False

    def duration(self) -> float:
        return max(self.end - self.begin, 0.0)


class SentenceSplitter:
    """Split raw text into shadowing-sized sentences."""

    PUNCT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
    EXTRA_SPLIT_RE = re.compile(r",|;|\band\b|\bbut\b|\bbecause\b|\bhowever\b", re.IGNORECASE)

    def __init__(self, min_words: int = 3, max_words: int = 18) -> None:
        self.min_words = min_words
        self.max_words = max_words

    def split(self, text: str) -> List[str]:
        raw_parts = [p.strip() for p in self.PUNCT_RE.split(text) if p.strip()]
        sentences: List[str] = []
        for part in raw_parts:
            words = part.split()
            if len(words) <= self.max_words:
                sentences.append(part)
                continue
            sentences.extend(self._split_long_sentence(words))
        merged: List[str] = []
        for part in sentences:
            if merged and len(part.split()) < self.min_words:
                merged[-1] = f"{merged[-1]} {part}".strip()
            else:
                merged.append(part)
        return merged

    def _split_long_sentence(self, words: List[str]) -> List[str]:
        chunks: List[str] = []
        start = 0
        while start < len(words):
            end = min(start + self.max_words, len(words))
            candidate = words[start:end]
            if end < len(words):
                remainder = " ".join(words[start:])
                splits = list(self.EXTRA_SPLIT_RE.finditer(remainder))
                if splits:
                    offset = splits[0].start()
                    offset_words = len(remainder[:offset].split())
                    end = start + max(offset_words, 1)
                    candidate = words[start:end]
            chunks.append(" ".join(candidate).strip())
            start = end
        return chunks


def estimate_alignment(sentences: List[str], audio_duration: float) -> List[Tuple[float, float]]:
    """Rudimentary alignment: distribute audio duration proportionally by word count."""

    word_counts = [max(len(s.split()), 1) for s in sentences]
    total_words = sum(word_counts) or 1
    cumulative = 0.0
    boundaries: List[Tuple[float, float]] = []
    for count in word_counts:
        start = cumulative
        portion = audio_duration * (count / total_words)
        end = start + portion
        boundaries.append((round(start, 3), round(end, 3)))
        cumulative = end
    if boundaries:
        last_start, _ = boundaries[-1]
        boundaries[-1] = (last_start, round(audio_duration, 3))
    return boundaries


def load_waveform(path: Path, width: int = 600, height: int = 140) -> List[int]:
    """Return a list of y-coordinates representing the waveform."""

    samples: List[int] = [height // 2] * width
    try:
        with wave.open(str(path), "rb") as wf:
            n_frames = wf.getnframes()
            if n_frames == 0:
                return samples
            raw = wf.readframes(n_frames)
            sample_width = wf.getsampwidth()
            step = max(n_frames // width, 1)
            import struct

            fmt = {1: "b", 2: "h", 4: "i"}.get(sample_width, "h")
            values = struct.iter_unpack(fmt, raw)
            points = []
            for idx, val in enumerate(values):
                if idx % step == 0:
                    points.append(val[0])
            if not points:
                return samples
            max_abs = max(abs(p) for p in points) or 1
            for i in range(min(width, len(points))):
                normalized = points[i] / max_abs
                y = int((1 - normalized) * (height / 2))
                samples[i] = y
    except Exception:
        pass
    return samples


class EditableTreeview(ttk.Treeview):
    """Treeview that allows double-click-to-edit cells."""

    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, **kwargs)
        self._edit_entry: Optional[tk.Entry] = None
        self.bind("<Double-1>", self._begin_edit)

    def _begin_edit(self, event: tk.Event) -> None:
        region = self.identify_region(event.x, event.y)
        if region != "cell":
            return
        row_id = self.identify_row(event.y)
        col_id = self.identify_column(event.x)
        if not row_id or not col_id:
            return
        x, y, width, height = self.bbox(row_id, col_id)
        value = self.set(row_id, col_id)
        self._edit_entry = tk.Entry(self)
        self._edit_entry.insert(0, value)
        self._edit_entry.place(x=x, y=y, width=width, height=height)
        self._edit_entry.focus()
        self._edit_entry.bind("<FocusOut>", lambda e: self._finish_edit(row_id, col_id))
        self._edit_entry.bind("<Return>", lambda e: self._finish_edit(row_id, col_id))

    def _finish_edit(self, row_id: str, col_id: str) -> None:
        if not self._edit_entry:
            return
        new_val = self._edit_entry.get()
        self.set(row_id, col_id, new_val)
        self._edit_entry.destroy()
        self._edit_entry = None


class ShadowingApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Shadowing English")
        self.geometry("1150x700")
        self.splitter = SentenceSplitter()
        self.section_path: Optional[Path] = None
        self.audio_path: Optional[Path] = None
        self.text_path: Optional[Path] = None
        self.sentences: List[Sentence] = []
        self.waveform_points: List[int] = []

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.setup_tab = ttk.Frame(notebook)
        self.practice_tab = ttk.Frame(notebook)
        notebook.add(self.setup_tab, text="Setup")
        notebook.add(self.practice_tab, text="Practice")

        self._build_setup_tab()
        self._build_practice_tab()

    # ------------------ UI builders ------------------
    def _build_setup_tab(self) -> None:
        container = ttk.Frame(self.setup_tab)
        container.pack(fill="both", expand=True, padx=6, pady=6)

        left = ttk.Frame(container, width=140)
        left.pack(side="left", fill="y", padx=(0, 8))
        for btn, cmd in [
            ("Open", self.open_lesson),
            ("Save section", self.save_section),
            ("Save as...", self.save_as_section),
            ("Save new talk", self.save_new_talk),
            ("Delete", self.delete_sentence),
        ]:
            ttk.Button(left, text=btn, command=cmd).pack(fill="x", pady=3)

        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)

        self.setup_tree = EditableTreeview(
            right,
            columns=("no", "begin", "end", "content", "confirm"),
            show="headings",
            selectmode="browse",
        )
        for col, heading, width in [
            ("no", "No", 70),
            ("begin", "Begin", 120),
            ("end", "End", 120),
            ("content", "Content", 600),
            ("confirm", "Confirm", 100),
        ]:
            self.setup_tree.heading(col, text=heading)
            self.setup_tree.column(col, width=width, anchor="w")
        self.setup_tree.pack(fill="x", pady=(0, 6))

        waveform_frame = ttk.Frame(right)
        waveform_frame.pack(fill="both", expand=True)

        self.waveform_canvas = tk.Canvas(waveform_frame, height=160, bg="white")
        self.waveform_canvas.pack(fill="x", pady=4)

        ctrl = ttk.Frame(waveform_frame)
        ctrl.pack(fill="x")
        for label in [
            "Câu 1",
            "◀▶",
            "Play",
            "Pause",
            "Stop",
            "Set",
            "Begin",
            "End",
            "Loop",
        ]:
            ttk.Button(ctrl, text=label).pack(side="left", padx=2)

        time_frame = ttk.Frame(waveform_frame)
        time_frame.pack(fill="x", pady=4)
        for label in ["<<", "<", "Set", "Begin", "End", ">", ">>"]:
            ttk.Button(time_frame, text=label).pack(side="left", padx=2)
        ttk.Label(time_frame, text="0.3s").pack(side="left", padx=4)

        zoom_frame = ttk.Frame(waveform_frame)
        zoom_frame.pack(fill="x")
        for label in ["Zoom in", "Zoom out", "Zoom to Fit", "-", "+", "🔍"]:
            ttk.Button(zoom_frame, text=label).pack(side="left", padx=2)

    def _build_practice_tab(self) -> None:
        container = ttk.Frame(self.practice_tab)
        container.pack(fill="both", expand=True, padx=6, pady=6)

        left = ttk.Frame(container, width=140)
        left.pack(side="left", fill="y", padx=(0, 8))
        for btn, cmd in [
            ("Open", self.open_lesson),
            ("Save section", self.save_section),
            ("Save as...", self.save_as_section),
            ("New talk", self.save_new_talk),
            ("Delete", self.delete_sentence),
        ]:
            ttk.Button(left, text=btn, command=cmd).pack(fill="x", pady=3)

        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)

        self.practice_tree = EditableTreeview(
            right,
            columns=("no", "content", "hide", "show"),
            show="headings",
            selectmode="browse",
        )
        for col, heading, width in [
            ("no", "No", 60),
            ("content", "Content", 620),
            ("hide", "Hide", 60),
            ("show", "Show", 60),
        ]:
            self.practice_tree.heading(col, text=heading)
            self.practice_tree.column(col, width=width, anchor="w")
        self.practice_tree.pack(fill="x", pady=(0, 6))

        dict_frame = ttk.Frame(right)
        dict_frame.pack(fill="x")
        ttk.Label(dict_frame, text="Dictionary", font=("Arial", 10, "bold")).pack(anchor="w")
        ttk.Label(dict_frame, text="Word list is generated from the loaded text.").pack(anchor="w")
        self.dict_tree = ttk.Treeview(dict_frame, columns=("word", "meaning"), show="headings")
        self.dict_tree.heading("word", text="Word")
        self.dict_tree.heading("meaning", text="Meaning (VI)")
        self.dict_tree.column("word", width=120)
        self.dict_tree.column("meaning", width=200)
        self.dict_tree.pack(fill="x", pady=4)

        waveform_frame = ttk.Frame(right)
        waveform_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.practice_canvas = tk.Canvas(waveform_frame, height=160, bg="white")
        self.practice_canvas.pack(fill="x", pady=4)

        speed_frame = ttk.Frame(waveform_frame)
        speed_frame.pack(fill="x")
        for speed in ["0.5x", "0.75x", "1.0x", "1.2x", "1.5x"]:
            ttk.Button(speed_frame, text=speed).pack(side="left", padx=2)
        ttk.Button(speed_frame, text="🔍-").pack(side="right", padx=2)
        ttk.Button(speed_frame, text="🔍+").pack(side="right", padx=2)

        ctrl = ttk.Frame(waveform_frame)
        ctrl.pack(fill="x")
        for label in [
            "Câu 1",
            "◀▶",
            "Play",
            "Pause",
            "Stop",
            "Loop",
        ]:
            ttk.Button(ctrl, text=label).pack(side="left", padx=2)

    # ------------------ Data handling ------------------
    def open_lesson(self) -> None:
        path = filedialog.askopenfilename(
            title="Open lesson",
            filetypes=[
                ("Section JSON", "*.json"),
                ("Audio", "*.wav *.mp3 *.ogg"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        selected = Path(path)
        if selected.suffix.lower() == ".json":
            self.load_section(selected)
            return

        self.audio_path = selected
        text_path_str = filedialog.askopenfilename(
            title="Open text file",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
        )
        if not text_path_str:
            messagebox.showwarning("Missing text", "Please select a text file to continue.")
            return
        self.text_path = Path(text_path_str)
        self.section_path = None
        self._prepare_from_audio_and_text()

    def _prepare_from_audio_and_text(self) -> None:
        assert self.audio_path and self.text_path
        try:
            text = self.text_path.read_text(encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Read error", f"Cannot read text file: {exc}")
            return
        sentence_texts = self.splitter.split(text)

        duration = self._audio_duration(self.audio_path)
        boundaries = estimate_alignment(sentence_texts, duration)
        self.sentences = [
            Sentence(idx=i + 1, begin=b, end=e, content=sentence_texts[i])
            for i, (b, e) in enumerate(boundaries)
        ]
        self.waveform_points = load_waveform(self.audio_path)
        self._refresh_tables()
        self._draw_waveforms()

    def _audio_duration(self, path: Path) -> float:
        try:
            with wave.open(str(path), "rb") as wf:
                return wf.getnframes() / float(wf.getframerate())
        except Exception:
            return 60.0

    def _refresh_tables(self) -> None:
        for tree in (self.setup_tree, self.practice_tree):
            for item in tree.get_children():
                tree.delete(item)

        for s in self.sentences:
            self.setup_tree.insert(
                "",
                "end",
                iid=str(s.idx),
                values=(s.idx, f"{s.begin:.3f}", f"{s.end:.3f}", s.content, "✓" if s.confirm else ""),
            )
            self.practice_tree.insert(
                "",
                "end",
                iid=str(s.idx),
                values=(s.idx, s.content, "", "✓" if s.confirm else ""),
            )

        self._refresh_dictionary()

    def _refresh_dictionary(self) -> None:
        for item in self.dict_tree.get_children():
            self.dict_tree.delete(item)
        words = self._unique_words()
        for word in words:
            self.dict_tree.insert("", "end", values=(word, "(translation placeholder)"))

    def _unique_words(self) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for sentence in self.sentences:
            for word in re.findall(r"[A-Za-z']+", sentence.content):
                lw = word.lower()
                if lw not in seen:
                    seen.add(lw)
                    ordered.append(word)
        return ordered

    def _draw_waveforms(self) -> None:
        for canvas in (self.waveform_canvas, self.practice_canvas):
            canvas.delete("all")
            width = int(canvas.winfo_width() or 800)
            height = int(canvas.winfo_height() or 160)
            points = self.waveform_points or [height // 2] * width
            if len(points) != width:
                scaled = []
                step = max(len(points) // width, 1)
                for i in range(width):
                    idx = min(i * step, len(points) - 1)
                    scaled.append(points[idx])
                points = scaled
            prev_x, prev_y = 0, points[0]
            for x, y in enumerate(points[1:], start=1):
                canvas.create_line(prev_x, prev_y, x, y, fill="#2f80ed")
                prev_x, prev_y = x, y

    # ------------------ Save/Load ------------------
    def save_section(self) -> None:
        if not self.sentences:
            messagebox.showinfo("Nothing to save", "Please open a lesson first.")
            return
        if self.section_path is None:
            self.save_as_section()
            return
        self._write_section(self.section_path)

    def save_as_section(self) -> None:
        if not self.sentences:
            messagebox.showinfo("Nothing to save", "Please open a lesson first.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not filename:
            return
        self.section_path = Path(filename)
        self._write_section(self.section_path)

    def save_new_talk(self) -> None:
        self.section_path = None
        self.audio_path = None
        self.text_path = None
        self.sentences = []
        self.waveform_points = []
        self._refresh_tables()
        self._draw_waveforms()

    def _write_section(self, path: Path) -> None:
        data = {
            "audio_path": str(self.audio_path) if self.audio_path else None,
            "text_path": str(self.text_path) if self.text_path else None,
            "sentences": [asdict(s) for s in self.sentences],
        }
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            messagebox.showinfo("Saved", f"Section saved to {path}")
        except Exception as exc:
            messagebox.showerror("Save error", f"Cannot save file: {exc}")

    def load_section(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Load error", f"Cannot read JSON: {exc}")
            return
        self.section_path = path
        audio_path = data.get("audio_path")
        text_path = data.get("text_path")
        self.audio_path = Path(audio_path) if audio_path else None
        self.text_path = Path(text_path) if text_path else None
        self.sentences = [
            Sentence(
                idx=idx + 1,
                begin=float(item.get("begin", 0.0)),
                end=float(item.get("end", 0.0)),
                content=str(item.get("content", "")),
                confirm=bool(item.get("confirm", False)),
            )
            for idx, item in enumerate(data.get("sentences", []))
        ]
        if self.audio_path and self.audio_path.exists():
            self.waveform_points = load_waveform(self.audio_path)
        else:
            self.waveform_points = []
        self._refresh_tables()
        self._draw_waveforms()

    # ------------------ Table actions ------------------
    def delete_sentence(self) -> None:
        selection = self.setup_tree.selection()
        if not selection:
            messagebox.showinfo("Select a row", "Please select a sentence to delete.")
            return
        idx = int(selection[0])
        self.sentences = [s for s in self.sentences if s.idx != idx]
        for new_idx, sentence in enumerate(self.sentences, start=1):
            sentence.idx = new_idx
        self._refresh_tables()


if __name__ == "__main__":
    app = ShadowingApp()
    app.mainloop()
