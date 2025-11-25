"""
sd_03R0_lesson_io.py

JSON I/O and lesson creation helpers for the Shadowing English app.

Important:
- NO speech recognition or Whisper calls.
- When creating a new lesson from text, all Begin/End are left as None.
"""

from __future__ import annotations

import json
import os
import re
from typing import List, Optional

from sd_02R0_models import (
    Sentence,
    DictionaryEntry,
    LessonData,
    renumber_sentences,
)


# ---------------------------------------------------------------------------
# JSON load / save
# ---------------------------------------------------------------------------


def load_lesson_from_json(path: str) -> LessonData:
    """
    Read a lesson JSON file and return a LessonData object.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    audio_path = data.get("audio_path")
    text_path = data.get("text_path")
    play_speed = float(data.get("play_speed", 1.0))
    last_selected_sentence = int(data.get("last_selected_sentence", 0))

    sentences: List[Sentence] = []
    for sec in data.get("sections", []):
        s = Sentence(
            id=int(sec.get("id", len(sentences) + 1)),
            begin=sec.get("begin"),
            end=sec.get("end"),
            text=sec.get("text", ""),
            confirmed=bool(sec.get("confirmed", False)),
            practice_mode=sec.get("practice_mode", "hide"),
            practice_text=sec.get("practice_text", sec.get("text", "")),
            original_text=sec.get("original_text", sec.get("text", "")),
            highlight_words=list(sec.get("highlight_words", [])),
        )
        sentences.append(s)

    dictionary: List[DictionaryEntry] = []
    for entry in data.get("dictionary", []):
        dictionary.append(
            DictionaryEntry(
                word=entry.get("word", ""),
                meaning_vi=entry.get("meaning_vi", ""),
            )
        )

    renumber_sentences(sentences)

    return LessonData(
        audio_path=audio_path,
        text_path=text_path,
        play_speed=play_speed,
        last_selected_sentence=last_selected_sentence,
        sentences=sentences,
        dictionary=dictionary,
    )


def save_lesson_to_json(lesson: LessonData, path: str) -> None:
    """
    Serialize a LessonData object to JSON file.
    """
    data = {
        "audio_path": lesson.audio_path,
        "text_path": lesson.text_path,
        "play_speed": lesson.play_speed,
        "last_selected_sentence": lesson.last_selected_sentence,
        "sections": [],
        "dictionary": [],
    }

    for s in lesson.sentences:
        data["sections"].append(
            {
                "id": s.id,
                "begin": s.begin,
                "end": s.end,
                "text": s.text,
                "confirmed": s.confirmed,
                "practice_mode": s.practice_mode,
                "practice_text": s.practice_text,
                "original_text": s.original_text,
                "highlight_words": s.highlight_words,
            }
        )

    for d in lesson.dictionary:
        data["dictionary"].append(
            {
                "word": d.word,
                "meaning_vi": d.meaning_vi,
            }
        )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Create sentences from text file (manual timing)
# ---------------------------------------------------------------------------


_SENTENCE_SPLIT_REGEX = re.compile(
    r"""(?<=[.!?])\s+""",  # split after ., !, ? followed by whitespace
    flags=re.MULTILINE,
)


def _split_text_into_sentences(text: str) -> List[str]:
    """
    Very simple sentence splitter based on punctuation.
    Returns a list of non-empty sentences (strings).
    """
    # Normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Merge multiple newlines into one space (so splitting works across lines)
    text = re.sub(r"\s*\n\s*", " ", text)
    parts = _SENTENCE_SPLIT_REGEX.split(text)
    sentences = []
    for part in parts:
        s = part.strip()
        if s:
            # ensure punctuation at end (optional)
            sentences.append(s)
    return sentences


def create_sentences_from_text(text_path: str) -> List[Sentence]:
    """
    Read a text file and create a list of Sentence objects.

    - Begin/End are None (manual timing).
    - practice_mode is "hide" by default.
    - practice_text is a masked version of original_text (e.g., underscores).
    """
    with open(text_path, "r", encoding="utf-8") as f:
        raw = f.read()

    text_sentences = _split_text_into_sentences(raw)

    sentences: List[Sentence] = []
    for i, line in enumerate(text_sentences, start=1):
        original = line.strip()
        # Simple mask: same length underscores (can be improved later)
        if original:
            practice_text = "_" * len(original)
        else:
            practice_text = ""

        s = Sentence(
            id=i,
            begin=None,
            end=None,
            text=original,
            confirmed=False,
            practice_mode="hide",
            practice_text=practice_text,
            original_text=original,
            highlight_words=[],
        )
        sentences.append(s)

    renumber_sentences(sentences)
    return sentences


# ---------------------------------------------------------------------------
# Optional helper: find matching JSON for an audio file
# ---------------------------------------------------------------------------


def find_matching_json_for_audio(audio_path: str) -> Optional[str]:
    """
    Try to find a JSON file in the same directory that shares the same stem
    as the given audio file.

    Example:
        audio_path = "/path/lesson01.mp3"
        -> looks for "/path/lesson01.json"

    Returns the json path if exists, otherwise None.
    """
    folder = os.path.dirname(audio_path)
    stem = os.path.splitext(os.path.basename(audio_path))[0]
    candidate = os.path.join(folder, f"{stem}.json")
    if os.path.isfile(candidate):
        return candidate
    return None
