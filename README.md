Shadowing English – Specification v1
====================================

Version: 1.0  
Scope: Desktop application (Tkinter / any UI toolkit) with two main tabs:
- Tab 1: Setup  
- Tab 2: Practice  

Important constraint:
- The app DOES NOT use any speech-recognition API (no Whisper, no OpenAI).
- All timing data (Begin/End) for each sentence is entered and fine-tuned manually in the Setup tab.


------------------------------------------------------------
I. Overall Objectives
------------------------------------------------------------

The Shadowing English app is designed to help learners practice “shadowing”:
listening to short English sentences and repeating them with proper timing and rhythm.

The application has two main phases:

1. Setup phase (Tab 1 – Setup)
   - The teacher or advanced user prepares a lesson from:
     - one audio file (English speech), and
     - one text file (the script).
   - The app splits the text into practice sentences/segments.
   - The user manually assigns Begin/End times for each sentence by listening to the audio.
   - The user can tweak the sentences, mark them as confirmed, and save everything to a JSON file (the “section file”).

2. Practice phase (Tab 2 – Practice)
   - The learner opens an existing lesson (JSON).
   - The app uses the pre-defined Begin/End times to play each sentence.
   - The learner practices shadowing each sentence:
     - Play / Loop sentence
     - Adjust playback speed (0.5x – 1.5x)
     - Hide/Show text (“gap filling” mode)
     - Refer to a small dictionary.

All AI / speech-to-text features are out of scope for this version. Timing is fully manual.


------------------------------------------------------------
II. Data Model and JSON Format
------------------------------------------------------------

The core of the application is the JSON lesson file (“section file”), which stores:

- Paths:
  - `audio_path` : string – absolute or relative path to the audio file.
  - `text_path`  : string – path to the original text script (optional).

- Global settings:
  - `play_speed`            : float – default playback speed (e.g. 1.0).
  - `last_selected_sentence`: integer – index of the last selected sentence (0-based or 1-based, implementation choice).

- Sections (sentences/segments):
  - `sections`: array of section objects. Each section has:
    - `id`            : integer – sentence index (1, 2, 3, …).
    - `begin`         : float or null – start time in seconds.
    - `end`           : float or null – end time in seconds.
    - `text`          : string – main sentence text (for Setup).
    - `original_text` : string – the full, correct version of the sentence (for Practice).
    - `practice_text` : string – the “masked” version of the sentence (for Hide mode).
    - `practice_mode` : string – `"hide"` or `"show"`.
    - `confirmed`     : boolean – whether the timing/content is confirmed by the teacher.
    - `highlight_words`: array of strings – words to highlight (future use).

- Dictionary:
  - `dictionary`: array of dictionary entry objects. Each entry has:
    - `word`       : string – English word.
    - `meaning_vi` : string – translation or definition (Vietnamese or any target language).


Time representation:
- Internally in JSON: seconds as floats, e.g. `3.65` means 3.650 seconds.
- Display format in the UI: `mm:ss.mmm`
  - Example: 3.65 seconds → `00:03.650`.


------------------------------------------------------------
III. Tab 1 – Setup
------------------------------------------------------------

1. Purpose
----------
The Setup tab is used by the teacher or advanced user to prepare a lesson from:
- an English audio file;
- a text script.

Main tasks:
1. Load audio + text or load an existing JSON lesson.
2. Split the text into reasonably sized sentences/segments for practice.
3. Manually assign Begin/End times for each sentence by listening to the audio.
4. Fine-tune the sentence content if needed.
5. Mark sentences as confirmed.
6. Save everything into a JSON file.


2. Main Workflow
----------------

2.1 Opening from JSON
- The user clicks **[Open]** and chooses to open an existing JSON lesson file.
- The app reads the JSON and restores:
  - `audio_path`, `text_path`
  - all `sections` with their fields (id, begin, end, text, confirmed, practice_mode, etc.)
  - `dictionary`, `play_speed`, `last_selected_sentence`
- The main Setup table is populated with one row per sentence:
  - Columns: No, Begin, End, Content, Confirm.
- If the audio or text file referenced by `audio_path` or `text_path` is missing:
  - Show a warning but still load the sentences so the user can review or edit them.

2.2 Creating a New Lesson from Audio + Text
- The user clicks **[Open]** and chooses:
  - Audio file (e.g. `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`).
  - Text file (e.g. `.txt`).
- The app:
  1. Clears any previous lesson from memory.
  2. Reads the text file and splits it into candidate sentences according to the rules in section 3.
  3. Creates a list of sentences where:
     - `id`         = incremental (1, 2, 3, …)
     - `text`       = the sentence content
     - `original_text` = same as text (initially)
     - `practice_text`  = underscore-based mask for practice (optional)
     - `begin` and `end` = `null` (no timing yet)
     - `confirmed`       = `false`
  4. Displays the sentences in the main Setup table (Begin/End cells are empty).

- Optional: Searching for a matching JSON file
  - After selecting audio + text, the app may try to find an existing JSON file with the same base name (e.g. `lesson01.mp3` ↔ `lesson01.json` in the same folder).
  - If found, ask:
    > “An existing setup file `xxx.json` was found for this audio. Do you want to load it?”
  - If the user clicks Yes:
    - Load from that JSON as in section 2.1 (overriding the newly split sentences).
  - If No:
    - Keep the newly generated sentences (timing still empty).


3. Text Splitting Rules (From Text File to Sentences)
-----------------------------------------------------

3.1 Input Characteristics
- The text file may be:
  - A continuous paragraph (no line breaks).
  - Multiple lines with or without punctuation.
- Punctuation such as `.`, `?`, `!` (possibly followed by `"`, `'`, `)`, `]`) marks potential sentence boundaries.

3.2 Basic Splitting
- Split on sentence-ending punctuation (`.`, `?`, `!`).
- Trim whitespaces.
- Discard empty lines or empty segments.
- Each non-empty segment becomes a candidate sentence.

3.3 Adjusting Length (Optional Heuristics)
- The app may use simple heuristics on word count to suggest segment lengths:
  - Very short sentences (e.g. < 4 words) may be merged with the next one.
  - Very long sentences (e.g. > 20–25 words) may be split at commas or conjunctions.
- Goal: each practice sentence roughly corresponds to 2–4 seconds of speech when read at normal pace.
- This is only a text-based heuristic. It does NOT measure actual audio length.


4. Main Setup Table
-------------------

4.1 Columns
- **No**      : “Sentence 1”, “Sentence 2”, … or simply the numeric ID.
- **Begin**   : Start time, displayed as `mm:ss.mmm`.
- **End**     : End time, displayed as `mm:ss.mmm`.
- **Content** : Sentence text to be shown in Setup.
- **Confirm** : A marker (e.g. `✓` or `○`) indicating whether the sentence is confirmed.

4.2 Row Selection
- Single-click on a row:
  - Sets this row as the current sentence.
  - Updates the sentence control bar (e.g. “Sentence 3”) and Begin/End fields.
  - Highlights the corresponding region in the waveform if timing is available.
- Double-click on a row:
  - Same as single-click + triggers play of the current sentence (if timing exists).

4.3 Editing Begin/End (Manual Timing)
- The user manually enters timing for each sentence.
- There are two input fields in the control bar:
  - **Begin:** text field with format `mm:ss.mmm`.
  - **End:**   text field with format `mm:ss.mmm`.
- The user can:
  - Type the time directly (e.g. `00:03.650`) and press Enter.
  - Adjust the time with small increment/decrement buttons:
    - Up arrow (`▲`): +0.01s (or +0.02s).
    - Down arrow (`▼`): -0.01s (or -0.02s), with lower bound at 0.000.
- When Begin/End is updated:
  - Convert the string `mm:ss.mmm` to seconds:
    - `total_seconds = minutes * 60 + seconds`.
  - Store `total_seconds` in the `begin`/`end` field for that sentence.
  - If `confirmed` was `true`, the app automatically sets it to `false` (the timing changed, so it should be re-confirmed).
  - The waveform highlight is updated.

4.4 Confirm Flag
- The Confirm column indicates whether the teacher has fully checked the sentence:
  - Timing is correct.
  - Content is acceptable.
- Typically:
  - A default symbol (e.g. `○`) for not confirmed.
  - A tick/check (e.g. `✓`) for confirmed.
- When Begin/End is modified after confirmation:
  - Reset `confirmed` to false.
- The exact UI action to toggle Confirm (clicking the cell, using a button, etc.) is up to implementation.

4.5 Editing Content
- The user can edit the sentence text in the Setup tab.
- Changing `text` or `original_text`:
  - Does NOT automatically change timing.
  - Does NOT necessarily change Confirm flag (this is optional behavior; can be either way).


5. Sentence Control Bar (Setup)
-------------------------------

5.1 Navigation and Playback
- Buttons:
  - `◄◄` Previous:
    - Move to the previous sentence (id - 1).
  - `Sentence n` (current sentence button):
    - Shows the current sentence ID: “Sentence 1”, “Sentence 2”, etc.
    - When clicked:
      - If `begin` and `end` exist and `begin < end`:
        - Play audio segment `[begin, end]`.
      - Otherwise:
        - Show a message: “This sentence has no valid Begin/End time.”
  - `❚❚` Pause/Resume:
    - Toggle pause/playback state.
  - `►►` Next:
    - Move to next sentence (id + 1).
  - `🔁` Loop:
    - When ON:
      - After the sentence finishes playing, automatically replay from `begin`.
    - When OFF:
      - Playback stops at `end`.

5.2 Timing Controls (Setup Only)
- Begin/End input fields:
  - Display current sentence’s `begin` and `end` in `mm:ss.mmm` format.
  - Support direct editing + Enter.
- Small adjustment buttons:
  - For Begin and End separately:
    - Up arrow: increase time by +0.01s.
    - Down arrow: decrease time by -0.01s (not below 0.0).
- Optional:
  - `Set Begin` and `Set End` buttons:
    - Grab the current audio playhead position and set it as begin or end.

5.3 Waveform Zoom
- Buttons:
  - `🔍+` Zoom In:
    - Increase zoom level, showing a more detailed waveform.
  - `🔍−` Zoom Out:
    - Decrease zoom level.
  - `⬜` Fit:
    - Scale waveform so the whole audio duration fits the visible area.

The Setup tab does not rely on any automatic timing or speech recognition. All Begin/End values come from the teacher’s manual input.


6. Open / Save Section
----------------------

6.1 Save Section (Quick Save)
- If `current_json_file` is already set:
  - Overwrite that JSON with the current lesson state.
- If not set:
  - Behave like “Save As”.

6.2 Save As
- Ask the user for a new file name and location (e.g. `lesson01.json`).
- Serialize and save:
  - `audio_path`, `text_path`, `play_speed`, `last_selected_sentence`.
  - `sections` array with full information.
  - `dictionary`.

6.3 New Talk (New Sentence)
- Add a new sentence after the current sentence.
- The new sentence:
  - Gets a new `id` (after renumbering).
  - `begin` = `null`, `end` = `null`.
  - `text`, `original_text`, `practice_text` = empty or some default.
  - `confirmed` = false.
- After insertion:
  - Renumber all sentences from 1..N.
  - Refresh both Setup and Practice tables.

6.4 Delete Sentence
- Delete the current sentence (after user confirmation).
- Renumber all sentences from 1..N.
- If the deleted sentence was the last one:
  - Adjust the current index to remain within bounds.
- Refresh tables and waveform highlight.


------------------------------------------------------------
IV. Tab 2 – Practice
------------------------------------------------------------

1. Purpose
----------
The Practice tab is the learner’s interface. It uses the lesson prepared in the Setup tab (JSON file) and allows the learner to:

- Play audio by sentences, based on `begin`/`end` times.
- Adjust playback speed (slow-down or speed-up).
- Toggle Hide/Show for each sentence to create gap-filling / partially hidden texts.
- Use a small dictionary for vocabulary reference.

No speech recognition is performed. The app does NOT attempt to compare the learner’s voice to the text.


2. Main Workflow
----------------

2.1 Loading a Lesson
- The Practice tab is typically used after:
  - The teacher has already created a lesson in Setup and saved it as JSON.
- When the app loads a JSON:
  - It restores paths, sections, dictionary, last selected sentence, and play speed.
  - The Practice table and Dictionary table are filled.

2.2 Selecting a Sentence
- The user clicks on a row in the Practice table:
  - The sentence becomes the current sentence.
  - The “Sentence n” button in the control bar updates accordingly.
  - The waveform highlights the `[begin, end]` region if timing is available.
- Double-clicking a row:
  - Equivalent to selecting + playing the sentence.

2.3 Practicing
- The learner:
  - Chooses the desired sentence.
  - Sets appropriate playback speed (e.g. 0.75x for slower, clearer practice).
  - Uses Hide/Show to reveal or hide parts of the sentence.
  - Uses Loop mode to repeat the sentence many times.
  - Shadows (repeats after) the sentence out loud.


3. Practice Table
-----------------

3.1 Columns
- **No**      : Sentence ID (1, 2, 3, …).
- **Content** : Text displayed to the learner. Depends on `practice_mode`.
- **Hide**    : Visual marker showing if the sentence is in “Hide” mode.
- **Show**    : Visual marker for “Show” mode.

3.2 Data Mapping
For each sentence in `sections`:

- `original_text`:
  - Full, correct sentence (e.g. “Could you fix it?”).

- `practice_text`:
  - Masked or gapped variant (e.g. “Could you _____ it?”).

- `practice_mode`:
  - `"hide"`:
    - Content displayed = `practice_text`.
    - Hide column = “●”
    - Show column = “○”
  - `"show"`:
    - Content displayed = `original_text`.
    - Hide column = “○”
    - Show column = “●”

3.3 Row Interaction
- Single-click:
  - Selects the sentence and updates current sentence controls and waveform highlight.
- Double-click:
  - Selects + plays based on Begin/End.

3.4 Toggling Hide/Show
- When the user interacts with the Hide or Show column (e.g. clicking):
  - If Hide chosen:
    - Set `practice_mode` = `"hide"` for that sentence.
  - If Show chosen:
    - Set `practice_mode` = `"show"`.
- After updating:
  - Refresh the Practice table row to reflect the new mode.
- This does NOT affect `begin`, `end`, or `confirmed`. It only changes how the text is displayed.


4. Audio Controls in Practice
-----------------------------

4.1 Navigation and Playback
- Controls are similar to Setup, but Practice does NOT have Begin/End editing fields.

Buttons:
- `◄◄` Previous:
  - Move to previous sentence (id - 1), select it in the Practice table.
- `Sentence n`:
  - Shows the current sentence number (e.g. “Sentence 5”).
  - When clicked:
    - If `begin` and `end` are valid floats and `begin < end`:
      - Play the segment `[begin, end]` using the current `playback_speed`.
    - Otherwise:
      - Show a message: “This sentence has no valid Begin/End. Please configure it in the Setup tab.”
- `❚❚` Pause/Resume:
  - Toggle pause/resume for current playback.
- `►►` Next:
  - Move to next sentence (id + 1), select and optionally auto-play (implementation choice).
- `🔁` Loop:
  - When ON:
    - After the current sentence finishes, automatically restart playback from `begin`.
  - When OFF:
    - Stop at `end`.

4.2 Playback Speed Controls
- Speed buttons: `0.5x`, `0.75x`, `1.0x`, `1.2x`, `1.5x`.
- At any time, only one speed is active (visually highlighted).
- When the user selects a speed:
  - Update `playback_speed`.
  - Future playback of sentences uses this speed.
- Default speed is `1.0x`.

4.3 Waveform Zoom (Same as Setup)
- `🔍+` Zoom In:
  - Increase zoom level to show more detail for a smaller time window.
- `🔍−` Zoom Out:
  - Decrease zoom level.
- `⬜` Fit:
  - Fit the entire audio into the waveform area.

4.4 No Timing Edits in Practice
- The Practice tab DOES NOT allow editing Begin/End.
- If timing is wrong:
  - The user must return to the Setup tab to fix it, then save the JSON and reload it in Practice.


5. Dictionary Panel
-------------------

5.1 Purpose
- Provide a quick reference for key vocabulary used in the lesson.
- Typically prepared by the teacher in Setup or via JSON.

5.2 Table Structure
- Columns:
  - **No.**   : Index (1, 2, 3, …).
  - **Word**  : English word.
  - **Meaning** : Explanation / translation (e.g. Vietnamese meaning).

5.3 Data Source
- Uses the `dictionary` array from JSON:
  ```json
  "dictionary": [
    { "word": "near", "meaning_vi": "gần" },
    { "word": "same", "meaning_vi": "giống" },
    ...
  ]
5.4 Interaction
- The dictionary in Practice is usually read-only.
- The learner can:
  - Scroll the list.
  - Optionally double-click a row to copy the word or show extra info.


6. Data Flow Between Tabs
-------------------------

6.1 From Setup to Practice
- Setup tab:
  - Creates/edits:
    - sections (with begin, end, text, original_text, practice_text, practice_mode, confirmed).
    - dictionary entries (word, meaning_vi).
  - Saves everything into JSON.

- Practice tab:
  - Loads the same JSON.
  - Uses begin/end for playback.
  - Uses practice_mode and text fields for display.
  - Shows dictionary as a read-only reference.

6.2 No speech recognition
- Neither Setup nor Practice performs speech recognition or auto alignment.
- No Whisper, no OpenAI calls for timing or evaluation.
- Any future pronunciation scoring is outside this spec.

6.3 Handling missing audio
- If audio_path does not point to an existing file:
  - Still load sentences and dictionary.
  - Any playback attempt shows a warning:
    - "Audio file not found. Please reconfigure the lesson in Setup."


------------------------------------------------------------
V. Implementation Notes (Non-binding)
------------------------------------------------------------

1. Time conversion utility
- Implement helpers:
  - float_seconds_to_str(sec) -> "mm:ss.mmm".
  - str_to_float_seconds("mm:ss.mmm") -> float or None.
- Reuse them everywhere.

2. Sentence renumbering
- After adding or deleting a sentence:
  - Assign IDs 1..N.
  - Update No column accordingly.

3. Error handling
- On invalid time string:
  - Show error and keep old value.
- On invalid range (begin >= end):
  - Do not play; show a clear error.

4. Persistence of UI state
- Optionally store:
  - last_selected_sentence.
  - play_speed.
- Restore these when reopening the lesson.

5. Cross-platform considerations
- UI toolkit is flexible (Tkinter, Qt, etc.).
- Layout and widgets can vary as long as behavior matches this spec.


------------------------------------------------------------
End of Specification
------------------------------------------------------------
