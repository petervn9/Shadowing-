"""
sd_02R0_models.py

Data models and helper functions for the Shadowing English app.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Sentence:
    """
    Represents a single practice sentence/segment in a lesson.
    """

    id: int
    begin: Optional[float]          # seconds, or None if not set
    end: Optional[float]            # seconds, or None if not set
    text: str                       # text used in Setup table
    confirmed: bool
    practice_mode: str              # "hide" or "show"
    practice_text: str              # masked version (for Practice tab)
    original_text: str              # full original sentence
    highlight_words: List[str]


@dataclass
class DictionaryEntry:
    """
    Represents one dictionary item (word + meaning in Vietnamese).
    """

    word: str
    meaning_vi: str


@dataclass
class LessonData:
    """
    Represents a full lesson: metadata + sentences + dictionary.
    """

    audio_path: Optional[str]
    text_path: Optional[str]
    play_speed: float
    last_selected_sentence: int
    sentences: List[Sentence]
    dictionary: List[DictionaryEntry]


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def format_time(seconds: Optional[float]) -> str:
    """
    Convert seconds (float) to string "mm:ss.mmm".
    If seconds is None, return empty string.
    """
    if seconds is None:
        return ""
    minutes = int(seconds // 60)
    secs = seconds % 60
    # secs is float, we want 2 digits before dot + 3 after
    return f"{minutes:02d}:{secs:06.3f}"


def parse_time(time_str: str) -> Optional[float]:
    """
    Parse "mm:ss.mmm" into seconds (float).
    Return None if string is empty or invalid.
    """
    if not time_str:
        return None
    try:
        parts = time_str.strip().split(":")
        if len(parts) != 2:
            return None
        minutes = float(parts[0])
        seconds = float(parts[1])
        return minutes * 60.0 + seconds
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Misc utilities
# ---------------------------------------------------------------------------


def renumber_sentences(sentences: List[Sentence]) -> None:
    """
    Ensure sentence.id is 1..N in list order.
    """
    for i, s in enumerate(sentences, start=1):
        s.id = i
