# Shadowing-
shadowing_English_for_To
1_Setup – Detailed Spec for the Setup Tab (Shadowing English App)
==================================================================

I. Overall Objective
--------------------
The **Setup** tab is used to prepare a shadowing lesson from:
- an English audio file, and
- a text file containing the lesson content.

Goals:
1. Let the user open simultaneously:
   - one English audio file (up to around 10 minutes),
   - one text file (a paragraph, not necessarily line–broken by sentence).
2. Automatically split the text into speaking units / sentences that are suitable for practice
   (2–4 seconds, enough context, not too short or too long).
3. Use the OpenAI Whisper API to recognize the audio and align text ↔ audio, proposing
   **Begin/End** timestamps for each sentence.
4. Display all results in the **main table**, allowing the user to:
   - listen to each sentence,
   - adjust Begin/End precisely,
   - edit the sentence text (Content),
   - mark sentences as reviewed (Confirm).
5. Save the entire setup result into one JSON file (section). This file will be reused by the Practice tab.

------------------------------------------------------------

II. Main Workflow
-----------------
1. The user clicks **[OPEN]**:
   - There are two main branches:

   (A) Open a new lesson from **audio + text**
   -----------------------------------------
   - The user selects:
     - one audio file (.mp3, .wav, ...),
     - one text file (.txt, ...).
   - The app clears the old table (if any), then:
     1. Reads the text file and splits it into sentences/segments according to the rules in section III.
     2. Sends the audio file to the OpenAI Whisper API for recognition.
     3. Matches Whisper’s transcript with the sentences from the text file (fuzzy match).
     4. Assigns Begin/End for each sentence if the match is good enough (≤ ~40% difference in word count).
     5. Builds the **main table**: `No | Begin | End | Content | Confirm`.

   - **Looking for an existing JSON** (if any):
     - After loading audio + text, the app tries to find a “closest” JSON file, for example:
       - in the same folder as the audio file,
       - with the same name as the audio, different extension
         (`lesson01.mp3` ↔ `lesson01.json`).
     - If found:
       - The app asks:
         > "A setup file `xxx.json` has been found for this audio. Do you want to load the setup from this file?"
       - If the user chooses **Yes**:
         - The app loads the full setup from that JSON (same as branch (B) below).
       - If **No**:
         - Keep the setup that was just created from audio + text (Whisper + sentence splitting).

   (B) Reopen a saved lesson from a **JSON section file**
   ------------------------------------------------------
   - The user directly selects a JSON file.
   - The app reads the JSON:
     - Retrieves `audio_path`, `text_path`.
     - If `audio_path` no longer exists → asks the user to select the corresponding audio again.
   - Restores:
     - The sentence list: id, Begin, End, Content, Confirm.
     - Other parameters (play_speed, volume, last_selected_sentence, … if any).
   - Rebuilds the main table and waveform, and reselects the last sentence (if stored).

2. After a lesson is opened (via A or B), the user uses:
   - The **main table** to select sentences, edit Content, tick Confirm, add/delete sentences.
   - The **sentence control bar** to play, move between sentences, loop.
   - The **time-adjust group** to fine–tune Begin/End.
   - The **waveform zoom group** to view waveform in detail or overall.

3. When satisfied, the user clicks:
   - **Save section** to quickly save into the current JSON file (overwrite), or
   - **Save as...** to save into a new JSON file (new name).

------------------------------------------------------------

III. Sentence Splitting Rules for the Text File
-----------------------------------------------
Goal: generate speaking units suitable for one breath (2–4 seconds), not too short or too long.

1. Input:
   - The text file is a paragraph and may:
     - contain multiple sentences on a single line,
     - have irregular line breaks.

2. Basic splitting:
   - Split by punctuation: `.`, `?`, `!` and common variants.
   - Additionally split by newline characters.

3. Handling overly long sentences:
   - Estimate duration by word count.
   - If the estimated length exceeds ~4 seconds (or word count is too high):
     - Further split at natural positions, with priority on:
       - commas, semicolons,
       - conjunctions: `and, but, because, so, however, ...`.
     - Try to avoid breaking unnatural units (e.g. not cutting inside "to + verb",
       "in the", "of the"... if possible).

4. Very short sentences:
   - May consider merging 2–3 short consecutive sentences if they form a continuous meaning
     (implementation details later).

5. Result after splitting:
   - A list of sentence strings, for example:
     - Sentence 1: "Good morning."
     - Sentence 2: "Morning, I tripped and broke the heel on this shoe."
     - Sentence 3: "Could you fix it?"
   - This list is used to fill the **Content** column of the main table.
   - The user can always edit Content manually; this does not affect auto–alignment.

------------------------------------------------------------

IV. Text ↔ Audio Alignment Using Whisper
----------------------------------------
1. Tool:
   - OpenAI Whisper API (online, sending the audio file to the server).
   - Audio language: English only.

2. Procedure:
   - Whisper receives the audio file and returns a transcript consisting of:
     - an array of segments, each with:
       - text (a sentence or group of sentences),
       - start_time and end_time.
   - The app matches each sentence in the Content list (from section III) with the transcript:
     - Uses fuzzy matching based on:
       - number of overlapping words,
       - percentage of matching words, word order, etc.
   - If the word count difference is ≤ ~40%:
     - Treat it as an acceptable match.
     - Assign:
       - Begin = segment start_time (optionally adjusted by a small safety margin, e.g. ±0.15 s),
       - End   = corresponding end_time.
   - If the difference > 40% or no good match is found:
     - Set Begin/End = empty (None).
     - The sentence still appears in the main table → user must assign Begin/End manually.

3. Result:
   - Each sentence in the main table has:
     - Begin and End (if match OK),
     - or empty Begin/End (needs manual setting).
   - Any sentence without Begin/End:
     - When clicked, will not play; it is only selected for editing.

------------------------------------------------------------

V. Main Table
-------------
Column structure:
1. **No**      – Sentence 1, 2, 3, ... (auto–renumber when adding/deleting).
2. **Begin**   – Start time, format `mm:ss.mmm` (e.g. `00:03.650`).
3. **End**     – End time, format `mm:ss.mmm`.
4. **Content** – Sentence text.
5. **Confirm** – Reviewed state (icon/tick).

Stored in JSON:
- Each sentence: `{ "id": n, "begin": float_seconds, "end": float_seconds, "text": "...", "confirmed": true/false }`.
- Time is stored as float seconds; when loading, the app formats it to `mm:ss.mmm`.

Behavior:
1. **Single–click** a row (e.g. Sentence 3):
   - Selects Sentence 3 as the current sentence.
   - Updates the **sentence control bar** (shows “Sentence 3”, corresponding Begin/End).
   - Highlights the waveform segment `[Begin → End]` (if Begin/End are defined).
   - Performs **auto zoom** on the waveform according to the 20–60–20 rule (see section VII).
   - Does **not** automatically play audio.

2. **Double–click** a row:
   - Performs everything that single–click does (select + highlight + auto zoom).
   - Then plays the `[Begin → End]` audio segment exactly once (unless Loop is on).

3. Sentence with no Begin/End (None):
   - Single/double–click only selects the sentence and updates the control bar.
   - Does not highlight waveform and does not play.

4. Editing **Content**:
   - The user can edit text at any time.
   - The app does **not** re–call Whisper and does not change Begin/End.
   - Confirm remains unchanged.

5. Ticking **Confirm**:
   - Indicates that the sentence has been fully reviewed (Begin/End + Content are satisfactory).
   - If the user later changes Begin/End of that sentence → the app automatically clears Confirm
     so the user will re–review it.

6. **New talk**:
   - Inserts a new sentence **directly below** the currently selected sentence:
     - Begin/End empty, Content empty, Confirm = False.
   - Renumbers No (Sentence 1, 2, 3…).

7. **Delete**:
   - Completely removes the selected sentence from the table.
   - Renumbers No for all sentences below.

------------------------------------------------------------

VI. Sentence Control Bar
------------------------
The sentence control bar is below the main table and consists of three groups:
- Sentence control group (left),
- Time adjustment group (center),
- Waveform zoom group (right).

A. Sentence Control Group (left)
--------------------------------
Buttons from left to right:

1. **Previous sentence** (⏮):
   - Moves the current selection to the previous sentence.
   - Example: current = Sentence 3 → press ⏮ → Sentence 2 becomes current.
   - When the sentence changes: main table, waveform, Begin/End, highlight, auto zoom… are
     all updated for the new sentence.
   - Does not automatically play audio.

2. **“Sentence X” button** (large green cell, e.g. “Sentence 3”):
   - Plays the `[Begin → End]` segment of the current sentence **exactly once**.
   - No loop if Loop is off.
   - If currently paused on this sentence → pressing again resumes from the pause position.

3. **Pause** (⏸):
   - Pauses playback of the current sentence (keeps the playhead position).
   - Press again on the Sentence X button or common Play to resume.

4. **Next sentence** (⏭):
   - Moves the current selection to the next sentence.
   - Example: Sentence 3 → Sentence 4.
   - When the sentence changes: table, waveform, Begin/End update, auto zoom, highlight new segment.
   - Does not automatically play audio.

5. **Loop** (🔁):
   - Toggles loop mode for the **current sentence**.
   - Loop OFF (normal icon): all play commands play the sentence once.
   - Loop ON  (highlighted icon):
     - Any play command for the current sentence (Sentence X button, common Play,
       double–click row, etc.) will loop the `[Begin → End]` segment until:
       - Loop is turned off, or
       - Stop is pressed.

B. Time Adjustment Group (center)
---------------------------------
1. **Set** (Begin) button:
   - Takes the current playhead position on the waveform and sets it as the `Begin`
     for the selected sentence.

2. **Begin** field:
   - Displays Begin in `mm:ss.mmm` format.
   - The user can type to edit directly.

3. **End** field:
   - Displays End in `mm:ss.mmm` format.
   - The user can type to edit directly.

4. **Set** (End) button:
   - Takes the current playhead position on the waveform and sets it as `End`
     for the selected sentence.

5. Small ▲ / ▼ buttons next to Begin/End:
   - Used to fine–tune Begin/End by **±0.010 s (10 ms)**.
   - Each press:
     - ▲ : increase by 0.010 s.
     - ▼ : decrease by 0.010 s.
   - When Begin/End changes:
     - If the sentence was Confirmed → the app automatically clears Confirm.

C. Waveform Zoom Group (right)
------------------------------
Consists of three buttons: Zoom In, Zoom Out, Fit to Window.

1. **Zoom In** (magnifier +):
   - Zooms in the time axis:
     - 1 second of audio occupies more pixels.
   - You see less time but in more detail (peaks, silences…).

2. **Zoom Out** (magnifier –):
   - Zooms out the time axis:
     - More seconds of audio fit into fewer pixels.
   - You see a longer time span but less detail.

3. **Fit to Window** (square frame):
   - Resets zoom to full view:
     - Shows the entire audio file from start to end fitting the waveform width.

Relationship with other functions:
- These three zoom buttons **only** affect how the waveform is displayed
  (time–to–pixel scale).
- They do **not** change Begin/End, Confirm, Loop, or Play state.
- Every time a new sentence is selected (from the main table or the sentence control bar):
  - The 20–60–20 auto zoom will run and **override** any current manual Zoom In/Out level.

------------------------------------------------------------

VII. Waveform Auto Zoom (20–60–20)
----------------------------------
Goal: whenever a sentence is selected, its `[Begin → End]` segment is always centered and takes up most of the view, while still showing a bit of audio before and after for context.

1. When does auto zoom run?
   - Whenever a **sentence is selected**:
     - Single–click a row in the main table,
     - Double–click a row,
     - Press previous/next sentence or Sentence X on the control bar.
   - When only adjusting Begin/End for the same sentence → **do not** auto zoom immediately.
   - To auto zoom again for the same sentence, the user can simply reselect it.

2. Display principle:
   - Segment `[Begin → End]` occupies about **60%** of the waveform width.
   - The part before Begin takes about **20%**.
   - The part after End takes about **20%**.
   - If the sentence is very short → zoom in strongly to still ensure about 60%.
   - If Begin is near the start or End is near the end of the file → prioritize showing
     the sentence clearly, without forcing the 20% before/after:
     - The view may be left–aligned or right–aligned.

3. Relationship with Play/Double–click:
   - Double–clicking a sentence or pressing Sentence X:
     - Performs auto zoom + highlight as in single–click,
     - Then plays the `[Begin → End]` segment.

------------------------------------------------------------

VIII. Keyboard Shortcuts and Playback
-------------------------------------
1. **Space**:
   - Play/Pause the `[Begin → End]` segment of the current sentence
     (same as Sentence X + Pause).

2. **←** / **→**:
   - Move the **playhead** on the waveform by ±0.3 s.
   - Begin/End remain unchanged.
   - Typically used together with Set Begin/Set End for precise timing.

3. Common Play button (on the player):
   - The Play (▶) button on the player:
     - Plays the `[Begin → End]` segment of the current sentence.
     - If Loop is ON → loops this segment until Stop or Loop OFF.

------------------------------------------------------------

IX. Save section / Save as... (JSON)
------------------------------------
1. Concept:
   - The app always has a notion of a “current JSON file” (current section file).
   - Initially, right after **Open audio + text** and before any save,
     current section file = None.

2. **Save section** – “Save with the same name”
----------------------------------------------
   - If a **current section file already exists** (opened from JSON or previously saved):
     - `Save section` will **directly overwrite** that JSON file without asking for a name.
   - If **no current section file yet** (first save after Open audio + text):
     - The app pops up a **save dialog for JSON** (same as Save as...):
       - Default folder = folder containing the audio file.
       - Suggested name = audio file name with `.json` extension.
     - After the user chooses a name and saves:
       - This file becomes the **current section file**.
       - Subsequent `Save section` presses overwrite this file.

3. **Save as...** – “Save with a new name”
-----------------------------------------
   - Always opens a dialog allowing the user to:
     - choose a folder,
     - set a **new JSON file name**.
   - After saving:
     - The new JSON becomes the **current section file**.
     - Future `Save section` operations overwrite this new file,
       no longer touching the old one.

4. JSON Content
---------------
   - JSON includes:
     - `audio_path`, `text_path`,
     - common properties (optional): `play_speed`, `volume`, `last_selected_sentence`, ...
     - a `sections` list:
       - id, begin, end, text, confirmed.

5. Re–opening from JSON (via **Open**)
--------------------------------------
   - When the user selects a JSON file in the Open dialog (branch B in section II):
     - The app reads the JSON and restores the entire setup.
     - That JSON file becomes the **current section file** for the session.
   - In the case of Open audio + text (branch A) where the app finds a JSON
     that matches the audio name:
     - If the user chooses **Yes** to load:
       - The JSON is loaded and becomes the **current section file**.
     - If **No**:
       - The JSON is not loaded; current section file = None
         until the user performs Save.

6. One audio file can have **multiple JSON versions** (multiple lesson variants), e.g.:
   - `lesson01.mp3` + `lesson01_easy.json`
   - `lesson01.mp3` + `lesson01_full.json`

------------------------------------------------------------

This document is the detailed specification for the **1_Setup** tab
of the English–learning application (Shadowing English).



2_Practice – Detailed Spec for the Practice Tab (Shadowing English App)
=======================================================================

I. Overall Objective
--------------------
The **Practice** tab is used to practice shadowing and sentence completion,
based on the sentence data prepared in the **Setup** tab.

Goals:
1. Let the user practice each sentence using the audio segment that has
   been cut (Begin/End) in Setup.
2. Practice using two modes:
   - **Hide**: listen → guess and gradually type each word into the blanks.
   - **Show**: view the original sentence to compare and look up new words.
3. Manage a vocabulary list (dictionary) based on lookups performed directly on the sentences.
4. Provide playback controls specialized for practice: loop per sentence,
   speed bar, convenient shortcuts.

The Practice tab **does not adjust Begin/End**; it only practices the content
already prepared in Setup.

------------------------------------------------------------------

II. Relationship between Setup & Practice Tabs
----------------------------------------------
1. Both tabs work on the **same lesson** (the same JSON file, called `current JSON`).
2. All operations **Open / Save section / Save as… / New talk / Delete**
   must be synchronized across both tabs.

3. When opening a new lesson:
   - **In Setup**:
     - Clicking **Open** can open either audio+text or a JSON file
       (according to the 1_Setup spec).
     - After opening, the active tab remains **Setup**, but Practice uses
       the same lesson.
   - **In Practice**:
     - Clicking **Open** is only used to open a **JSON file**.
       Audio+text cannot be opened here.
     - After opening, the active tab remains **Practice**, and Setup
       is synchronized to the same lesson.

4. When the user is working on a lesson and then clicks Open to load another:
   - The app does not ask again.
   - It **automatically runs Save section** (overwriting `current JSON`)
     before opening the new lesson.

5. Saving data:
   - **Save section**: overwrites `current JSON` (regardless of whether it
     is clicked in Setup or Practice).
   - **Save as…**: always asks for a new JSON file name, and the new file
     then becomes `current JSON`.
   - The saved data always includes **both Setup and Practice**:
     - Setup: Begin/End, Content, Confirm, ...
     - Practice: practice_mode, practice_text, highlights, dictionary, ...

------------------------------------------------------------------

III. Practice Table
-------------------
### 1. Structure of the Practice Table
Columns:

1. **No**
   - Sentence 1, 2, 3… same as in Setup.
   - Automatically renumbered whenever sentences are added or deleted.

2. **Content**
   - Displays the sentence being practiced.
   - Has two display modes: **Hide** and **Show** (see details below).

3. **Hide / Show**
   - Each sentence has one group of **radio buttons**:
     - `Hide` – practice fill–in–the–blanks, using `practice_text`.
     - `Show` – view the original sentence and look up words, using `original_text`.

### 2. Internal State per Sentence (Practice)
Each sentence (in addition to Setup data) has:

- `original_text`: the original sentence (copied from Setup, read–only).
- `practice_text`: the practice sentence (what the learner types).
- `practice_mode`: `"hide"` or `"show"`.
- `highlight_words`: list of words/tokens to highlight in yellow in Show mode.

> Upon first switching from Setup to Practice:
> - All sentences have `practice_mode` = "hide".
> - `practice_text` is initialized from `original_text` by turning each word into `_____`.

### 3. Hide Mode
Goal: **listen → guess & type words**.

- The **Content** cell is displayed based on `practice_text`:
  - The sentence is treated as a sequence of “word slots” separated by spaces.
  - **Slot not yet filled** → displayed as `_____`.
  - **Slot that has been typed** → shows the **actual typed word**, no underscore.
    - Example initial: `Could you ______ it?`
    - After typing `fix`: `Could you fix it?`
- The learner can type and edit directly in the Content cell:
  - Whenever they can hear a word, they type it in the correct slot.
  - They may delete or edit it later if they realize it was wrong.
- `practice_text` is always stored in the JSON:
  - Switch to Show then back to Hide → everything they typed remains unchanged.

### 4. Show Mode
Goal: **view the original sentence & look up words**.

- The **Content** cell displays `original_text` plus yellow highlights
  on words that have been looked up.
- `practice_text` is not shown in this mode.
- This mode is used to:
  - compare with what was typed in Hide,
  - select words to look up English–Vietnamese meaning.

> When switching from Show back to Hide:
> - The Content cell returns to displaying `practice_text` (no loss of typed text).

### 5. Clicking Sentences in the Practice Table
Behavior is the same as in the main table in Setup:

- **Single–click** a row (Sentence 3):
  - Selects Sentence 3 as the current sentence.
  - Updates the sentence control bar (shows "Sentence 3").
  - Highlights the waveform segment `[Begin → End]` for Sentence 3.
  - Auto zooms the waveform according to the 20–60–20 rule.
  - Does **not** automatically play.

- **Double–click** a row:
  - Performs all effects of a single–click.
  - Then **plays the `[Begin → End]` segment** of that sentence
    (respecting the Loop state).

### 6. New talk & Delete from the Practice Tab
- **New talk** (clicked in Practice):
  - Inserts a new sentence **directly below** the currently selected sentence
    in **both Setup & Practice**.
  - Setup:
    - Begin/End empty.
    - Content empty.
    - Confirm = False.
  - Practice:
    - `original_text` initially empty (or synced when the user later edits Setup).
    - `practice_mode` = "hide".
    - `practice_text` empty or all underscores once text exists.
  - Renumbers No in both tabs.

- **Delete** (clicked in Practice):
  - Completely removes the selected sentence from the **entire lesson**:
    - Removes from the Setup table.
    - Removes from the Practice table.
  - Renumbers No in both tabs.
  - If that sentence contained highlighted words:
    - Those highlights disappear with the sentence.
    - The **dictionary remains unchanged** (the word and its Vietnamese meaning are not deleted).

------------------------------------------------------------------

IV. Dictionary Table
--------------------
### 1. Structure
- The table is on the right side of the Practice UI and has three columns:
  1. **No** – index: 1, 2, 3… in lookup order.
  2. **Word** – the English word/phrase (stored in lower–case).
  3. **Meaning (VI)** – short Vietnamese meaning specific to this lesson.

- In JSON, stored as a unique list, e.g.:
  ```jsonc
  "dictionary": [
    { "word": "same",          "meaning_vi": "giống" },
    { "word": "many",          "meaning_vi": "nhiều" },
    { "word": "single-family", "meaning_vi": "nhà riêng" }
  ]
2. Creating Entries (Alt + D / Lookup)

Dictionary entries are created/edited only through sentences in Show mode.

Procedure:

In Show mode, the learner selects a word or phrase in the Content cell.

Can be:

A single word: same, work.

A hyphenated word: single-family.

A multi–word phrase: New York
(stored as lower–case new york).

Press Alt + D or right–click → "Lookup".

The app:

Normalizes the selected Word to lower–case for matching
(Work & work → work).

Looks up an English–Vietnamese dictionary to get a short
meaning for this lesson.

If the Word is not yet in the dictionary:

Adds a new row with Word + Meaning(VI).

No increments sequentially (in order of lookup).

If the Word already exists:

Does not create a new row.

Does not change the existing meaning.

At the same time:

In that sentence, the word/phrase that was looked up is highlighted in yellow
in Show mode.

This highlight info is stored in the sentence’s highlight_words.

3. Editing / Deleting Dictionary Entries

Manual editing of Word or Meaning(VI) by double–clicking cells is not allowed.

There is a Delete button for the dictionary:

Deletes the currently selected row from the dictionary table.

When deleting:

The app removes all yellow highlights for that Word in every sentence,
because it no longer exists in the dictionary.

The dictionary renumbers its No values.

4. Clicking a Dictionary Entry

Single–click a row in the dictionary:

Plays audio pronunciation of that Word (via TTS or dictionary audio;
implementation later).

Does not change the current sentence or filter the Practice table.

The dictionary is a one–way reference list and does not directly affect
sentence selection.

V. Sentence Control Bar & Waveform (Practice Tab)

The Practice tab uses the same basic layout as Setup (sentence control,
zoom group, waveform, auto zoom), but with some behavioral differences
to better support practice.

1. Sentence Control Buttons (left group)

Layout is the same as in Setup:

Previous sentence (⏮):

In Practice:

Moves to the previous sentence (Sentence N → N–1).

Auto zooms waveform (20–60–20) for that sentence.

Highlights [Begin → End] for the new sentence.

Automatically plays the sentence once.

If Loop is ON → enters loop mode.

“Sentence X” (green cell):

Plays [Begin → End] of the current sentence once if Loop is OFF.

If Loop is ON → starts looping (see below).

If currently paused → pressing again resumes playback.

Pause (⏸):

Pauses playback for the current sentence (keeping the playhead).

Press Sentence X or Space to resume.

Next sentence (⏭):

In Practice:

Moves to the next sentence (Sentence N → N+1).

Auto zooms and highlights that sentence.

Automatically plays the sentence once.

If Loop is ON → enters loop mode.

Loop (🔁):

Toggles loop mode for the current sentence.

Loop ON:

Each loop consists of:

Playing [Begin → End],

Waiting a short gap (~0.5–1.0 seconds, e.g. ~0.7 s)
so the learner can shadow,

Playing again from Begin.

Continues until:

Loop is turned OFF (button or key L),

or Stop/Pause,

or the user switches to another sentence.

The Loop icon changes appearance (color/state) to indicate ON/OFF.

2. Speed Bar (playback speed) – Practice only

Located above the waveform, with buttons:

0.5x | 0.75x | 1.0x | 1.2x | 1.5x

Default: 1.0x (1.0x button is highlighted).

When clicking a button:

All subsequent playback/loop uses the new speed.

Does not change Begin/End or the current sentence.

Speed is not saved to JSON:

Each time a lesson is opened → speed resets to 1.0x.

3. Waveform & Zoom

The Zoom group (Zoom In, Zoom Out, Fit to Window) and the
20–60–20 auto zoom rule share the same logic as in Setup:

When a new sentence is selected (single/double–click in Practice table,
pressing previous/next sentence, pressing Sentence X):

Waveform auto zooms so that [Begin → End] occupies ~60% of the width,
with ~20% before Begin and ~20% after End.

If the sentence is very short → strong zoom in.

If Begin is near start or End near end of file →
prioritize displaying the sentence clearly rather than forcing exact 20%.

When only Begin/End are adjusted in Setup for the same sentence →
Practice does not auto zoom immediately until the user selects that sentence again.

Scrubbing (dragging the playhead) on the waveform in Practice:

Only moves the playhead.

Does not change Begin/End.

Does not change the current sentence.

VI. Keyboard Shortcuts in the Practice Tab

Shortcuts shared with Setup:

Space:

Play/Pause the [Begin → End] segment of the current sentence
(equivalent to Sentence X + Pause).

← / →:

Move the playhead by ±0.3 s.

Begin/End remain unchanged.

Additional shortcuts specific to Practice:

L:

Toggle Loop for the current sentence (same as clicking 🔁).

↑ (Up):

Move to the previous sentence (same as the previous sentence button):

Change sentence, auto zoom + highlight,

Automatically play once (or loop if Loop is ON).

↓ (Down):

Move to the next sentence (same as the next sentence button):

Change sentence, auto zoom + highlight,

Automatically play once (or loop if Loop is ON).

This document is the detailed specification for the 2_Practice tab
of the English–learning application (Shadowing English), including:

The Practice Table,

The Dictionary,

The sentence control bar, waveform, zoom, and speed bar,

And the behavior of Open / Save / New talk / Delete in the Practice tab.
