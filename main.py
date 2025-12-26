"""
Typing trainer with live words per minute feedback.

This module provides a Tkinter based typing trainer. It loads a list of
training texts from a file, allows the user to select a text, and then measures
the words per minute (WPM) while the user types. Completed session WPM values
are stored in a statistics file and can be visualized.
"""

from __future__ import annotations

import random
import string
import time
import textwrap
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, List, TYPE_CHECKING
import ctypes
from ctypes import wintypes
import sys
import threading

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

if TYPE_CHECKING:
    from transformers.pipelines import TextGenerationPipeline

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

try:
    import winreg
except ImportError:
    winreg = None

GA_ROOT = 2
WCA_USEDARKMODECOLORS = 26


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t)
    ]

GUI_WINDOW_XY = "1350x550"
TEXT_FILE_NAME = "typing_texts.txt"
STATS_FILE_NAME = "typing_stats.csv"
LETTER_STATS_FILE_NAME = "letter_stats.csv"
SPECIAL_STATS_FILE_NAME = "special_character_stats.csv"
NUMBER_STATS_FILE_NAME = "number_stats.csv"
TRAINING_FLAG_COLUMN = "is_training_run"
STATS_FILE_HEADER = (
    f"timestamp;wpm;error_percentage;duration_seconds;{TRAINING_FLAG_COLUMN}"
)
LETTER_STATS_FILE_HEADER = (
    "timestamp;letters_per_minute;error_percentage;"
    f"duration_seconds;{TRAINING_FLAG_COLUMN}"
)
SPECIAL_STATS_FILE_HEADER = (
    "timestamp;specials_per_minute;error_percentage;"
    f"duration_seconds;{TRAINING_FLAG_COLUMN}"
)
NUMBER_STATS_FILE_HEADER = (
    "timestamp;digits_per_minute;error_percentage;"
    f"duration_seconds;{TRAINING_FLAG_COLUMN}"
)
SUDDEN_DEATH_TYPING_STATS_FILE_NAME = "sudden_death_typing_stats.csv"
SUDDEN_DEATH_LETTER_STATS_FILE_NAME = "sudden_death_letter_stats.csv"
SUDDEN_DEATH_SPECIAL_STATS_FILE_NAME = "sudden_death_special_stats.csv"
SUDDEN_DEATH_NUMBER_STATS_FILE_NAME = "sudden_death_number_stats.csv"
SUDDEN_DEATH_TYPING_STATS_FILE_HEADER = (
    "timestamp;wpm;correct_characters;duration_seconds;"
    f"completed;{TRAINING_FLAG_COLUMN}"
)
SUDDEN_DEATH_LETTER_STATS_FILE_HEADER = (
    "timestamp;letters_per_minute;correct_letters;duration_seconds;"
    f"completed;{TRAINING_FLAG_COLUMN}"
)
SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER = (
    "timestamp;specials_per_minute;correct_symbols;duration_seconds;"
    f"completed;{TRAINING_FLAG_COLUMN}"
)
SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER = (
    "timestamp;digits_per_minute;correct_digits;duration_seconds;"
    f"completed;{TRAINING_FLAG_COLUMN}"
)
STATS_FILTER_OPTIONS = [
    ("regular_only", "Non-training runs"),
    ("training_only", "Training runs"),
    ("all_runs", "All runs"),
]
DEFAULT_STATS_FILTER_KEY = "regular_only"
STATS_FILTER_LABEL_BY_KEY = {
    key: label for key, label in STATS_FILTER_OPTIONS
}
STATS_FILTER_KEY_BY_LABEL = {
    label: key for key, label in STATS_FILTER_OPTIONS
}
DEFAULT_FONT_FAMILY = "Courier New"
DEFAULT_FONT_SIZE = 12
MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 48
LETTER_SEQUENCE_LENGTH = 100
LETTER_MODE_CHARACTERS = string.ascii_letters + "\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc"
SPECIAL_SEQUENCE_LENGTH = 100
SPECIAL_MODE_CHARACTERS = string.punctuation + "\u00a7\u00b2\u00b3"
NUMBER_SEQUENCE_LENGTH = 100
TARGET_TEXT_DISPLAY_WIDTH = 90
TARGET_TEXT_LINE_LENGTH = 80
RANDOM_TEXT_LABEL = "Random Text"
RANDOM_TEXT_CHAR_LIMIT = 300
RANDOM_MAX_GENERATIONS = 4
TEXT_GENERATION_MODEL_NAME = "distilgpt2"
TEXT_GENERATION_MAX_LENGTH = 200
TEXT_GENERATION_TEMPERATURE = 0.95
TEXT_GENERATION_TOP_P = 0.92
TEXT_GENERATION_TOP_K = 50
LIGHT_THEME = {
    "background": "#f4f4f4",
    "surface": "#ffffff",
    "text": "#111111",
    "muted_text": "#333333",
    "accent": "#3a7afe",
    "button_background": "#e1e1e1",
    "button_foreground": "#111111",
    "button_active_background": "#d0d0d0",
    "input_background": "#ffffff",
    "input_foreground": "#111111",
    "select_background": "#cde2ff",
    "select_foreground": "#111111",
    "error_background": "#ffd6d6",
    "error_foreground": "#7a0000",
    "border": "#c0c0c0",
    "titlebar_color": "#f1f1f1",
    "titlebar_text": "#111111",
    "titlebar_border": "#c0c0c0"
}
DARK_THEME = {
    "background": "#121212",
    "surface": "#1f1f1f",
    "text": "#f4f4f4",
    "muted_text": "#c6c6c6",
    "accent": "#569cd6",
    "button_background": "#333333",
    "button_foreground": "#f4f4f4",
    "button_active_background": "#3f3f3f",
    "input_background": "#1f1f1f",
    "input_foreground": "#f4f4f4",
    "select_background": "#264f78",
    "select_foreground": "#f4f4f4",
    "error_background": "#5c1b1b",
    "error_foreground": "#ffb4b4",
    "border": "#3a3a3a",
    "titlebar_color": "#1f1f1f",
    "titlebar_text": "#f4f4f4",
    "titlebar_border": "#333333"
}

PLOT_LIGHT_THEME = {
    "figure_facecolor": "#f5f5f5",
    "axes_facecolor": "#ffffff",
    "text_color": "#111111",
    "spine_color": "#cbcbcb",
    "grid_color": "#d8d8d8",
    "hist_speed_color": "#3a7afe",
    "hist_error_color": "#f59542",
    "hist_correct_color": "#2ca58d",
    "bar3d_color": "#4f6d7a",
    "daily_speed_color": "#3a7afe",
    "daily_error_color": "#f79646",
    "daily_duration_color": "#2ca58d",
    "time_per_day_bar_color": "#7fb3d5",
    "time_cumulative_line_color": "#0d3b66",
    "heatmap_low_color": "#ffffff",
    "heatmap_high_color": "#0d3b66",
    "heatmap_bad_color": "#f0f0f0",
    "annotation_face_color": "#ffffff",
    "annotation_edge_color": "#333333",
    "annotation_text_color": "#111111",
    "toolbar_background": "#e9e9e9",
    "toolbar_button_background": "#d6d6d6",
    "toolbar_button_active": "#c2c2c2",
    "pie_mode_colors": ["#4f6d7a", "#7b8c5f", "#b7a57a", "#9a8c98"],
    "pie_training_colors": ["#547c8c", "#a0606a"],
    "legend_facecolor": "#ffffff",
    "legend_edgecolor": "#cbcbcb"
}

PLOT_DARK_THEME = {
    "figure_facecolor": "#0f1115",
    "axes_facecolor": "#181b21",
    "text_color": "#f5f5f5",
    "spine_color": "#464a52",
    "grid_color": "#30343c",
    "hist_speed_color": "#64b5f6",
    "hist_error_color": "#ffb74d",
    "hist_correct_color": "#81c784",
    "bar3d_color": "#5dade2",
    "daily_speed_color": "#64b5f6",
    "daily_error_color": "#ffb74d",
    "daily_duration_color": "#81c784",
    "time_per_day_bar_color": "#4f7cac",
    "time_cumulative_line_color": "#ffd166",
    "heatmap_low_color": "#121418",
    "heatmap_high_color": "#26c6da",
    "heatmap_bad_color": "#1b1f26",
    "annotation_face_color": "#1f232a",
    "annotation_edge_color": "#f5f5f5",
    "annotation_text_color": "#f5f5f5",
    "toolbar_background": "#1b1f26",
    "toolbar_button_background": "#2c313c",
    "toolbar_button_active": "#394152",
    "pie_mode_colors": ["#64b5f6", "#81c784", "#ffd166", "#f28e85"],
    "pie_training_colors": ["#26c6da", "#b39ddb"],
    "legend_facecolor": "#1f232a",
    "legend_edgecolor": "#555555"
}


def get__file_path(file_path: str) -> Path:
    """
    Return the path of the given file.

    The function tries to place the file next to this script. If that is not
    possible, it falls back to the current working directory.
    """
    try:
        base_dir = Path(__file__).resolve().parent
    except NameError:
        base_dir = Path.cwd()
    return base_dir / file_path


def default_texts() -> List[str]:
    """
    Return a list of default training texts.

    These texts are written to the storage file on first run so that the user
    can start training immediately. Texts may contain multiple lines, but here
    all defaults are single line texts.
    """
    return [
        "The quick brown fox jumps over the lazy dog.",
        "Typing practice helps to increase speed and accuracy.",
        "Python is a powerful and readable programming language.",
        "Consistent practice is the key to becoming a faster typist.",
        "Robots can move precisely if their controllers are "
        "well designed."
    ]


def _parse_multiline_texts(raw: str) -> List[str]:
    """
    Parse the raw content of the text file into a list of texts.

    Consecutive non empty lines form one text. Empty lines separate texts.
    Trailing spaces at the end of lines are removed.
    """
    texts: List[str] = []
    current_lines: List[str] = []

    for line in raw.splitlines():
        if line.strip() == "":
            if current_lines:
                joined = "\n".join(current_lines).rstrip("\n")
                texts.append(joined)
                current_lines = []
        else:
            current_lines.append(line.rstrip())

    if current_lines:
        joined = "\n".join(current_lines).rstrip("\n")
        texts.append(joined)

    return texts


def load_or_create_texts(path: Path) -> List[str]:
    """
    Load training texts from the given file, creating it with defaults if needed.

    Each text is a block of non empty lines. Empty lines separate texts.
    """
    if not path.exists():
        lines = default_texts()
        content = "\n\n".join(lines)
        path.write_text(content, encoding="utf-8")
        return lines

    raw = path.read_text(encoding="utf-8")
    texts = _parse_multiline_texts(raw)

    if not texts:
        texts = default_texts()
        content = "\n\n".join(texts)
        path.write_text(content, encoding="utf-8")

    return texts


def ensure_stats_file_header(
    path: Path,
    header: str,
    create_if_missing: bool = True
) -> None:
    """
    Make sure the statistics file exists and starts with the given header line.

    If the file is missing and creation is allowed, the header line is written.
    When the file already exists but lacks the requested header, the header is
    inserted as the first line while preserving the existing data.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        if create_if_missing:
            path.write_text(f"{header}\n", encoding="utf-8")
        return

    with path.open("r+", encoding="utf-8") as file:
        first_line = file.readline().strip()
        if first_line == header:
            return
        file.seek(0)
        existing_content = file.read()
        file.seek(0)
        file.write(f"{header}\n")
        file.write(existing_content)


class TypingTrainerApp:
    """
    Tkinter application that provides a typing trainer with live WPM and stats.

    User selects a text, sees it displayed, and types it into an input
    field. As soon as the first character is typed, the application starts
    timing and continuously updates the WPM value. Wrong characters are
    highlighted in red. When the text is complete and correct, the timer
    stops, the WPM value is frozen, and the result is stored in a statistics
    file. A histogram of all stored WPM values can be shown.
    """

    def __init__(self, master: tk.Tk, texts: List[str]) -> None:
        """
        Initialize the GUI and internal state.

        :param master: Root Tkinter window.
        :param texts: List of training texts.
        """
        self.master = master
        self.texts = texts

        self.selected_text: str = ""
        self.target_text: str = ""
        self.start_time: float | None = None
        self.update_job_id: str | None = None
        self.finished: bool = False
        self.stats_file_path: Path = get__file_path(STATS_FILE_NAME)
        self.letter_stats_file_path: Path = get__file_path(LETTER_STATS_FILE_NAME)
        self.special_stats_file_path: Path = get__file_path(
            SPECIAL_STATS_FILE_NAME
        )
        self.number_stats_file_path: Path = get__file_path(NUMBER_STATS_FILE_NAME)
        self.sudden_death_typing_stats_file_path: Path = get__file_path(
            SUDDEN_DEATH_TYPING_STATS_FILE_NAME
        )
        self.sudden_death_letter_stats_file_path: Path = get__file_path(
            SUDDEN_DEATH_LETTER_STATS_FILE_NAME
        )
        self.sudden_death_special_stats_file_path: Path = get__file_path(
            SUDDEN_DEATH_SPECIAL_STATS_FILE_NAME
        )
        self.sudden_death_number_stats_file_path: Path = get__file_path(
            SUDDEN_DEATH_NUMBER_STATS_FILE_NAME
        )

        self.current_font_size: int = DEFAULT_FONT_SIZE
        self.text_font: tkfont.Font | None = None
        self.text_generator: TextGenerationPipeline | None = None
        self.text_generator_loading: bool = False

        self.error_count: int = 0
        self.correct_count: int = 0
        self.previous_text: str = ""
        self.is_letter_mode: bool = False
        self.letter_sequence: List[str] = []
        self.letter_index: int = 0
        self.letter_total_letters: int = 0
        self.letter_errors: int = 0
        self.letter_correct_letters: int = 0
        self.letter_previous_text: str = ""
        self.is_special_mode: bool = False
        self.special_sequence: List[str] = []
        self.special_index: int = 0
        self.special_total_chars: int = 0
        self.special_errors: int = 0
        self.special_correct_chars: int = 0
        self.is_number_mode: bool = False
        self.number_sequence: List[str] = []
        self.number_index: int = 0
        self.number_total_digits: int = 0
        self.number_errors: int = 0
        self.number_correct_digits: int = 0
        self.last_session_mode: str = "typing"
        self.style = ttk.Style()
        self.dark_mode_enabled: bool = self._detect_system_dark_mode()
        self.dark_mode_var = tk.BooleanVar(
            master=self.master,
            value=self.dark_mode_enabled
        )
        self.sudden_death_var = tk.BooleanVar(master=self.master, value=False)
        self.training_run_var = tk.BooleanVar(master=self.master, value=False)
        default_filter_label = STATS_FILTER_LABEL_BY_KEY[DEFAULT_STATS_FILTER_KEY]
        self.stats_filter_var = tk.StringVar(
            master=self.master,
            value=default_filter_label
        )
        self.sudden_death_failure_triggered: bool = False
        self._title_bar_refresh_job: str | None = None

        self._build_gui()
        self._schedule_generator_warmup()


    def _build_gui(self) -> None:
        """
        Create all GUI widgets.
        """
        self.master.title("Typing Trainer")

        self.master.geometry(GUI_WINDOW_XY)

        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.master, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(0, 10))

        ttk.Label(list_frame, text="Available texts").grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 5)
        )

        self.text_listbox = tk.Listbox(
            list_frame,
            height=20,
            width=30,
            exportselection=False
        )
        self.text_listbox.grid(row=1, column=0, sticky="ns")

        self.text_listbox.insert(tk.END, RANDOM_TEXT_LABEL)

        for idx, text in enumerate(self.texts, start=1):
            first_line = text.splitlines()[0] if text.splitlines() else text
            preview = (
                first_line if len(first_line) <= 40 else first_line[:37] + "..."
            )
            self.text_listbox.insert(tk.END, f"{idx:02d}  {preview}")

        button_frame = ttk.Frame(list_frame)
        button_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        load_button = ttk.Button(
            button_frame,
            text="Load selected",
            command=self.on_load_selected
        )
        load_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        random_button = ttk.Button(
            button_frame,
            text="Load random",
            command=self.on_load_random,
        )
        random_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(2, weight=1)

        top_right_frame = ttk.Frame(right_frame)
        top_right_frame.grid(row=0, column=0, sticky="ew")
        top_right_frame.columnconfigure(0, weight=1)
        top_right_frame.columnconfigure(1, weight=0)
        top_right_frame.columnconfigure(2, weight=0)
        top_right_frame.columnconfigure(3, weight=0)
        top_right_frame.columnconfigure(4, weight=0)
        top_right_frame.columnconfigure(5, weight=0)

        self.info_label = ttk.Label(
            top_right_frame,
            text="Select a text on the left and click Load."
        )
        self.info_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Font size control buttons
        font_smaller_button = ttk.Button(
            top_right_frame,
            text="T-",
            width=3,
            command=self.decrease_font_size
        )
        font_smaller_button.grid(row=0, column=1, padx=(5, 2), sticky="e")

        font_reset_button = ttk.Button(
            top_right_frame,
            text="T0",
            width=3,
            command=self.reset_font_size
        )
        font_reset_button.grid(row=0, column=2, padx=2, sticky="e")

        font_bigger_button = ttk.Button(
            top_right_frame,
            text="T+",
            width=3,
            command=self.increase_font_size
        )
        font_bigger_button.grid(row=0, column=3, padx=(2, 0), sticky="e")
        self.dark_mode_toggle = ttk.Checkbutton(
            top_right_frame,
            text="Dark mode",
            variable=self.dark_mode_var,
            command=self.toggle_dark_mode
        )
        self.dark_mode_toggle.grid(row=0, column=4, padx=(10, 0), sticky="e")
        self.sudden_death_toggle = ttk.Checkbutton(
            top_right_frame,
            text="Sudden death",
            variable=self.sudden_death_var,
            command=self.on_sudden_death_toggle
        )
        self.sudden_death_toggle.grid(row=0, column=5, padx=(10, 0), sticky="e")

        self.wpm_label = ttk.Label(
            right_frame,
            text="Time: 0.0 s  |  WPM: 0.0  |  Errors: 0  |  Error %: 0.0"
        )
        self.wpm_label.grid(row=1, column=0, sticky="e")

        self.display_text = tk.Text(
            right_frame,
            height=6,
            width=TARGET_TEXT_DISPLAY_WIDTH,
            wrap="word",
            state="disabled"
        )
        self.display_text.grid(row=2, column=0, sticky="nsew")

        # Block copying from the target text widget to force real typing of the user
        copy_commands = [
            "<<Copy>>",
            "<Control-c>",
            "<Control-C>",
            "<Command-c>",
            "<Command-C>",
            "<Control-Insert>"
        ]
        for sequence in copy_commands:
            self.display_text.bind(sequence, self._block_target_copy)

        input_frame = ttk.LabelFrame(right_frame, text="Your input")
        input_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)

        self.input_text = tk.Text(
            input_frame,
            height=8,
            wrap="word"
        )
        self.input_text.grid(row=0, column=0, sticky="nsew")

        # Tag for highlighting incorrect characters (also spaces)
        self.input_text.tag_configure(
            "error",
            foreground="red",
            background="#ffcccc"
        )

        self.input_text.bind("<Key>", self.on_key_press)

        control_frame = ttk.Frame(right_frame)
        control_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        for idx in range(12):
            control_frame.columnconfigure(idx, weight=0)
        control_frame.columnconfigure(11, weight=1)

        reset_button = ttk.Button(
            control_frame,
            text="Reset session",
            command=self.handle_reset_button
        )
        reset_button.grid(row=0, column=0, padx=(0, 5))

        training_toggle = ttk.Checkbutton(
            control_frame,
            text="Training run",
            variable=self.training_run_var
        )
        training_toggle.grid(row=0, column=1, padx=(0, 5))

        histogram_button = ttk.Button(
            control_frame,
            text="Typing text stats",
            command=self.show_stats
        )
        histogram_button.grid(row=0, column=2, padx=(5, 0))

        letter_mode_button = ttk.Button(
            control_frame,
            text="Letter mode",
            command=self.start_letter_mode
        )
        letter_mode_button.grid(row=0, column=3, padx=(5, 0))

        letter_stats_button = ttk.Button(
            control_frame,
            text="Letter stats",
            command=self.show_letter_stats
        )
        letter_stats_button.grid(row=0, column=4, padx=(5, 0))

        special_mode_button = ttk.Button(
            control_frame,
            text="Special char mode",
            command=self.start_special_mode
        )
        special_mode_button.grid(row=0, column=5, padx=(5, 0))

        special_stats_button = ttk.Button(
            control_frame,
            text="Special char stats",
            command=self.show_special_stats
        )
        special_stats_button.grid(row=0, column=6, padx=(5, 0))

        number_mode_button = ttk.Button(
            control_frame,
            text="Number mode",
            command=self.start_number_mode
        )
        number_mode_button.grid(row=0, column=7, padx=(5, 0))

        number_stats_button = ttk.Button(
            control_frame,
            text="Number stats",
            command=self.show_number_stats
        )
        number_stats_button.grid(row=0, column=8, padx=(5, 0))

        general_stats_button = ttk.Button(
            control_frame,
            text="General stats",
            command=self.show_general_stats
        )
        general_stats_button.grid(row=0, column=9, padx=(5, 0))

        stats_filter_label = ttk.Label(control_frame, text="Stats filter:")
        stats_filter_label.grid(row=0, column=10, padx=(10, 0), sticky="e")

        stats_filter_values = [label for _, label in STATS_FILTER_OPTIONS]
        self.stats_filter_combobox = ttk.Combobox(
            control_frame,
            textvariable=self.stats_filter_var,
            values=stats_filter_values,
            state="readonly",
            width=18
        )
        self.stats_filter_combobox.grid(row=0, column=11, padx=(5, 0), sticky="ew")

        # Initialize shared font for both text widgets
        self.text_font = tkfont.Font(
            family=DEFAULT_FONT_FAMILY,
            size=self.current_font_size
        )
        self.display_text.configure(font=self.text_font)
        self.input_text.configure(font=self.text_font)
        self._apply_theme()

    def _get_stats_filter_key(self) -> str:
        """
        Return the internal key of the currently selected statistics filter.
        """
        label = self.stats_filter_var.get()
        return STATS_FILTER_KEY_BY_LABEL.get(label, DEFAULT_STATS_FILTER_KEY)

    def _should_include_training_entry(self, is_training_run: bool) -> bool:
        """
        Determine whether the given entry should be used based on the filter.
        """
        filter_key = self._get_stats_filter_key()
        if filter_key == "training_only":
            return is_training_run
        if filter_key == "regular_only":
            return not is_training_run
        return True

    @staticmethod
    def _parse_training_flag(parts: List[str], flag_index: int) -> bool:
        """
        Safely parse the training flag from a CSV row.
        """
        if len(parts) <= flag_index:
            return False
        value = parts[flag_index].strip().lower()
        return value in {"1", "true", "yes", "y"}


    def _set_info_text(self, text: str) -> None:
        """
        Safely update the info label from any thread.
        """
        def _apply() -> None:
            self.info_label.configure(text=text)

        self.master.after(0, _apply)


    def _schedule_generator_warmup(self) -> None:
        """
        Kick off a background warm-up for the text generator.
        """
        self.master.after(500, self._start_generator_warmup_thread)


    def _start_generator_warmup_thread(self) -> None:
        if self.text_generator is not None:
            return

        threading.Thread(
            target=self._warm_up_generator_worker,
            name="random-text-warmup",
            daemon=True
        ).start()


    def _warm_up_generator_worker(self) -> None:
        self._ensure_text_generator(show_errors=False)


    def _block_target_copy(self, event: tk.Event) -> str:
        """
        Prevent copying from the target display widget.
        """
        return "break"


    def increase_font_size(self) -> None:
        """
        Increase the font size of the text widgets by one step.
        """
        if self.current_font_size >= MAX_FONT_SIZE:
            return
        self.current_font_size += 2
        self._apply_font_size()


    def decrease_font_size(self) -> None:
        """
        Decrease the font size of the text widgets by one step.
        """
        if self.current_font_size <= MIN_FONT_SIZE:
            return
        self.current_font_size -= 2
        self._apply_font_size()


    def reset_font_size(self) -> None:
        """
        Reset the font size of the text widgets to the default value.
        """
        self.current_font_size = DEFAULT_FONT_SIZE
        self._apply_font_size()


    def _apply_font_size(self) -> None:
        """
        Apply the currently configured font size to both text widgets.
        """
        if self.text_font is not None:
            self.text_font.configure(size=self.current_font_size)

    def toggle_dark_mode(self) -> None:
        """
        Enable or disable the dark theme for the UI.
        """
        self.dark_mode_enabled = bool(self.dark_mode_var.get())
        self._apply_theme()

    def is_sudden_death_active(self) -> bool:
        """
        Return True if the sudden death toggle is enabled.
        """
        return bool(self.sudden_death_var.get())

    def on_sudden_death_toggle(self) -> None:
        """
        React to sudden death activation by resetting the current session.
        """
        enabled = self.is_sudden_death_active()
        self.reset_session(clear_display=False)
        if enabled:
            self.info_label.configure(
                text="Sudden death enabled. Load a text or start a mode."
            )
        else:
            self.info_label.configure(
                text="Sudden death disabled. Normal sessions restored."
            )

    def _apply_theme(self) -> None:
        """
        Apply the currently selected color theme to Tk and ttk widgets.
        """
        theme = DARK_THEME if self.dark_mode_enabled else LIGHT_THEME

        try:
            self.style.theme_use("clam")
        except tk.TclError:
            # Fall back to the original theme if clam is unavailable.
            pass

        self.master.configure(bg=theme["background"])

        # ttk widget styling
        self.style.configure("TFrame", background=theme["background"])
        self.style.configure(
            "TLabel",
            background=theme["background"],
            foreground=theme["text"]
        )
        self.style.configure(
            "TButton",
            background=theme["button_background"],
            foreground=theme["button_foreground"]
        )
        self.style.map(
            "TButton",
            background=[
                ("active", theme["button_active_background"]),
                ("pressed", theme["button_active_background"])
            ]
        )
        self.style.configure(
            "TLabelframe",
            background=theme["background"],
            foreground=theme["text"],
            bordercolor=theme["border"]
        )
        self.style.configure(
            "TLabelframe.Label",
            background=theme["background"],
            foreground=theme["text"]
        )
        self.style.configure(
            "TCheckbutton",
            background=theme["background"],
            foreground=theme["text"]
        )

        # Classic Tk widgets require manual configuration.
        self.display_text.configure(
            background=theme["surface"],
            foreground=theme["text"],
            insertbackground=theme["text"],
            highlightbackground=theme["border"],
            highlightcolor=theme["accent"],
            selectbackground=theme["select_background"],
            selectforeground=theme["select_foreground"]
        )
        self.input_text.configure(
            background=theme["input_background"],
            foreground=theme["input_foreground"],
            insertbackground=theme["text"],
            highlightbackground=theme["border"],
            highlightcolor=theme["accent"],
            selectbackground=theme["select_background"],
            selectforeground=theme["select_foreground"]
        )
        self.input_text.tag_configure(
            "error",
            foreground=theme["error_foreground"],
            background=theme["error_background"]
        )
        self.text_listbox.configure(
            background=theme["surface"],
            foreground=theme["text"],
            selectbackground=theme["select_background"],
            selectforeground=theme["select_foreground"],
            highlightbackground=theme["border"],
            highlightcolor=theme["accent"],
            activestyle="none"
        )
        self._apply_title_bar_colors(theme)
        self._schedule_title_bar_refresh()

    def _detect_system_dark_mode(self) -> bool:
        """
        Return the OS default preference for app dark mode when available.
        """
        if sys.platform != "win32" or winreg is None:
            return False
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return int(value) == 0
        except OSError:
            return False

    def _get_plot_palette(self) -> dict[str, Any]:
        """
        Return the Matplotlib palette for the currently selected theme.
        """
        return PLOT_DARK_THEME if self.dark_mode_enabled else PLOT_LIGHT_THEME

    def _apply_title_bar_colors(self, theme: dict[str, str]) -> None:
        """
        Ensure the root window's title bar matches the current theme.
        """
        try:
            self.master.update_idletasks()
        except tk.TclError:
            pass
        self._set_native_title_bar_theme(
            self.master,
            self.dark_mode_enabled,
            {
                "titlebar_color": theme["titlebar_color"],
                "titlebar_text": theme["titlebar_text"],
                "titlebar_border": theme["titlebar_border"]
            }
        )

    def _schedule_title_bar_refresh(self) -> None:
        """
        Queue another title-bar sync once the window is fully realized.
        """
        if self._title_bar_refresh_job is not None:
            try:
                self.master.after_cancel(self._title_bar_refresh_job)
            except tk.TclError:
                pass
        self._title_bar_refresh_job = self.master.after(
            250,
            self._refresh_title_bar_theme
        )

    def _refresh_title_bar_theme(self) -> None:
        """
        Callback that reapplies the theme to the title bar.
        """
        self._title_bar_refresh_job = None
        theme = DARK_THEME if self.dark_mode_enabled else LIGHT_THEME
        self._apply_title_bar_colors(theme)

    @staticmethod
    def _hex_to_colorref(color: str) -> int:
        """
        Convert a #RRGGBB color string into a Windows COLORREF integer.
        """
        color = color.lstrip("#")
        if len(color) != 6:
            return 0
        red = int(color[0:2], 16)
        green = int(color[2:4], 16)
        blue = int(color[4:6], 16)
        return (blue << 16) | (green << 8) | red

    def _set_native_title_bar_theme(
        self,
        widget: tk.Misc | None,
        dark: bool,
        colors: dict[str, str] | None = None
    ) -> None:
        """
        Attempt to align the OS-managed title bar with the current theme.

        Windows exposes this through the DWM immersive dark mode flag. Other
        platforms keep their default styling.
        """
        if widget is None or sys.platform != "win32":
            return
        try:
            hwnd = widget.winfo_id()
        except Exception:
            return
        try:
            user32 = ctypes.windll.user32
        except (AttributeError, OSError):
            return
        try:
            ancestor = user32.GetAncestor(wintypes.HWND(hwnd), GA_ROOT)
            if ancestor:
                hwnd = ancestor
        except Exception:
            pass
        dwmapi = None
        try:
            dwmapi = ctypes.windll.dwmapi
        except (AttributeError, OSError):
            pass
        value = ctypes.c_int(1 if dark else 0)
        hwnd_handle = wintypes.HWND(hwnd)
        applied = False
        if dwmapi is not None:
            for attribute in (20, 19):  # Windows 11/10 attribute IDs
                try:
                    result = dwmapi.DwmSetWindowAttribute(
                        hwnd_handle,
                        ctypes.c_uint(attribute),
                        ctypes.byref(value),
                        ctypes.sizeof(value)
                    )
                    if result == 0:
                        applied = True
                        break
                except Exception:
                    continue
            if applied and colors:
                caption = wintypes.DWORD(
                    self._hex_to_colorref(colors.get("titlebar_color", ""))
                )
                text_color = wintypes.DWORD(
                    self._hex_to_colorref(colors.get("titlebar_text", ""))
                )
                border = wintypes.DWORD(
                    self._hex_to_colorref(colors.get("titlebar_border", ""))
                )
                try:
                    dwmapi.DwmSetWindowAttribute(
                        hwnd_handle,
                        ctypes.c_uint(35),  # DWMWA_CAPTION_COLOR
                        ctypes.byref(caption),
                        ctypes.sizeof(caption)
                    )
                    dwmapi.DwmSetWindowAttribute(
                        hwnd_handle,
                        ctypes.c_uint(36),  # DWMWA_TEXT_COLOR
                        ctypes.byref(text_color),
                        ctypes.sizeof(text_color)
                    )
                    dwmapi.DwmSetWindowAttribute(
                        hwnd_handle,
                        ctypes.c_uint(34),  # DWMWA_BORDER_COLOR
                        ctypes.byref(border),
                        ctypes.sizeof(border)
                    )
                except Exception:
                    pass
        if not applied:
            try:
                set_comp_attr = user32.SetWindowCompositionAttribute
            except AttributeError:
                set_comp_attr = None
            if set_comp_attr:
                try:
                    data = WINDOWCOMPOSITIONATTRIBDATA()
                    data.Attribute = WCA_USEDARKMODECOLORS
                    data.Data = ctypes.cast(ctypes.byref(value), ctypes.c_void_p)
                    data.SizeOfData = ctypes.sizeof(value)
                    set_comp_attr(hwnd_handle, ctypes.byref(data))
                except Exception:
                    pass

    def _apply_plot_theme(
        self,
        fig: plt.Figure,
        palette: dict[str, Any]
    ) -> None:
        """
        Apply the palette colors to figure, axes, ticks, and labels.
        """
        text_color = palette["text_color"]
        fig.patch.set_facecolor(palette["figure_facecolor"])
        for ax in fig.axes:
            try:
                ax.set_facecolor(palette["axes_facecolor"])
            except Exception:
                pass
            ax.tick_params(colors=text_color)
            if hasattr(ax, "xaxis"):
                ax.xaxis.label.set_color(text_color)
            if hasattr(ax, "yaxis"):
                ax.yaxis.label.set_color(text_color)
            if hasattr(ax, "zaxis"):
                ax.zaxis.label.set_color(text_color)
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_color(text_color)
            if hasattr(ax, "get_zticklabels"):
                for label in ax.get_zticklabels():
                    label.set_color(text_color)
            if hasattr(ax, "title"):
                ax.title.set_color(text_color)
            if hasattr(ax, "spines"):
                for spine in ax.spines.values():
                    spine.set_color(palette["spine_color"])
            grid_lines = getattr(ax, "get_xgridlines", lambda: [])()
            grid_lines += getattr(ax, "get_ygridlines", lambda: [])()
            for line in grid_lines:
                line.set_color(palette["grid_color"])
        self._style_matplotlib_toolbar(fig, palette)

    def _set_widget_colors(
        self,
        widget: tk.Misc | None,
        *,
        background: str,
        foreground: str,
        active_background: str | None = None
    ) -> None:
        """
        Best-effort theming for Tk widgets that may be part of Matplotlib toolbars.
        """
        if widget is None:
            return
        for option in ("background", "bg"):
            try:
                widget.configure(**{option: background})
                break
            except tk.TclError:
                continue
        for option in ("foreground", "fg"):
            try:
                widget.configure(**{option: foreground})
                break
            except tk.TclError:
                continue
        if active_background is not None:
            try:
                widget.configure(activebackground=active_background)
            except tk.TclError:
                pass
            try:
                widget.configure(activeforeground=foreground)
            except tk.TclError:
                pass

    def _style_matplotlib_toolbar(
        self,
        fig: plt.Figure,
        palette: dict[str, Any]
    ) -> None:
        """
        Apply theme colors to the Matplotlib toolbar and its containing window.
        """
        manager = getattr(fig.canvas, "manager", None)
        if manager is None:
            return
        toolbar = getattr(manager, "toolbar", None)
        if toolbar is not None:
            self._set_widget_colors(
                toolbar,
                background=palette["toolbar_background"],
                foreground=palette["text_color"]
            )
            for child in toolbar.winfo_children():
                self._set_widget_colors(
                    child,
                    background=palette["toolbar_button_background"],
                    foreground=palette["text_color"],
                    active_background=palette["toolbar_button_active"]
                )
            message_label = getattr(toolbar, "_message_label", None)
            self._set_widget_colors(
                message_label,
                background=palette["toolbar_background"],
                foreground=palette["text_color"]
            )
        window = getattr(manager, "window", None)
        if window is not None:
            self._set_native_title_bar_theme(
                window,
                self.dark_mode_enabled,
                {
                    "titlebar_color": palette["axes_facecolor"],
                    "titlebar_text": palette["text_color"],
                    "titlebar_border": palette["spine_color"]
                }
            )

    def _style_legend(self, legend, palette: dict[str, Any]) -> None:
        """
        Apply theme colors to a legend if it exists.
        """
        if legend is None:
            return
        frame = legend.get_frame()
        if frame is not None:
            frame.set_facecolor(palette["legend_facecolor"])
            frame.set_edgecolor(palette["legend_edgecolor"])
        for text in legend.get_texts():
            text.set_color(palette["text_color"])

    def _configure_figure_window(self, fig: plt.Figure) -> None:
        """
        Center a Matplotlib figure and limit its window size to 80% of screen.
        """
        manager = getattr(fig.canvas, "manager", None)
        if manager is None:
            return
        window = getattr(manager, "window", None)
        if window is None:
            return

        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        if screen_width <= 0 or screen_height <= 0:
            return

        target_width = int(screen_width * 0.8)
        target_height = int(screen_height * 0.8)

        pos_x = int((screen_width - target_width) / 2)
        pos_y = int((screen_height - target_height) / 2)

        try:
            window.wm_geometry(f"{target_width}x{target_height}+{pos_x}+{pos_y}")
        except Exception:
            pass


    def on_load_selected(self) -> None:
        """
        Load the text that is currently selected in the listbox.
        """
        selection = self.text_listbox.curselection()
        if not selection:
            messagebox.showinfo(
                "Selection",
                "Please select a text in the list."
            )
            return

        index = selection[0]
        self._load_text_from_index(index)


    def on_load_random(self) -> None:
        """
        Load a random text from the list of available texts.
        """
        total_entries = len(self.texts) + 1
        index = random.randrange(total_entries)
        self.text_listbox.selection_clear(0, tk.END)
        self.text_listbox.selection_set(index)
        self._load_text_from_index(index)


    def _load_text_from_index(self, index: int) -> None:
        """
        Resolve the listbox index to a text string and display it.
        """
        total_entries = len(self.texts) + 1
        if index < 0 or index >= total_entries:
            messagebox.showinfo(
                "Selection",
                "The selected text could not be loaded."
            )
            return

        if index == 0:
            generated_text = self._generate_random_sentence_text()
            if not generated_text:
                if self.text_generator_loading:
                    messagebox.showinfo(
                        "Random text",
                        "The random text generator is still starting up. "
                        "Please try again in a moment."
                    )
                else:
                    messagebox.showinfo(
                        "Random text",
                        "Unable to generate a random text right now."
                    )
                return
            self.selected_text = generated_text
        else:
            real_index = index - 1
            self.selected_text = self.texts[real_index]

        self._apply_loaded_text()


    def _ensure_text_generator(
        self,
        show_errors: bool = True
    ) -> TextGenerationPipeline | None:
        """
        Lazily initialize and cache the Hugging Face text-generation pipeline.
        """
        if self.text_generator is not None:
            return self.text_generator

        if self.text_generator_loading:
            return None

        self.text_generator_loading = True
        self._set_info_text(
            "Preparing random text generator. First use may take a minute..."
        )

        try:
            from transformers import pipeline

            self.text_generator = pipeline(
                "text-generation",
                model=TEXT_GENERATION_MODEL_NAME,
                device=-1,
                framework="pt"
            )
        except Exception:
            self.text_generator = None
            if show_errors:
                self.master.after(
                    0,
                    lambda: messagebox.showerror(
                        "Random text",
                        "The transformer model could not be initialized. "
                        "Please verify that transformers/torch are installed "
                        "and that the model weights can be downloaded."
                    )
                )
        finally:
            self.text_generator_loading = False

        if self.text_generator is not None:
            self._set_info_text(
                "Random text generator ready. Start typing in the input area."
            )
        else:
            self._set_info_text(
                "Random text generator unavailable. Select a stored text."
            )

        return self.text_generator


    def _generate_random_sentence_text(
        self,
        target_length: int = RANDOM_TEXT_CHAR_LIMIT
    ) -> str:
        """
        Build a text out of transformer-generated sequences up to the target length.
        """
        generator = self._ensure_text_generator(show_errors=True)
        if generator is None:
            return ""

        pieces: List[str] = []
        attempts = 0
        while (
            len(" ".join(pieces)) < target_length
            and attempts < RANDOM_MAX_GENERATIONS
        ):
            snippet = self._sample_transformer_text(generator)
            attempts += 1
            if not snippet:
                continue
            pieces.append(snippet)

        combined = " ".join(pieces).strip()
        if not combined:
            return ""

        return self._trim_generated_text(combined, target_length)


    def _sample_transformer_text(
        self,
        generator: TextGenerationPipeline
    ) -> str:
        """
        Sample a short passage from the text-generation pipeline.
        """
        prompt = self._build_generator_prompt(generator)
        try:
            outputs = generator(
                prompt,
                max_length=TEXT_GENERATION_MAX_LENGTH,
                do_sample=True,
                temperature=TEXT_GENERATION_TEMPERATURE,
                top_p=TEXT_GENERATION_TOP_P,
                top_k=TEXT_GENERATION_TOP_K,
                num_return_sequences=1,
                pad_token_id=generator.tokenizer.eos_token_id
            )
        except Exception:
            return ""

        if not outputs:
            return ""

        text = outputs[0].get("generated_text", "")
        if prompt and text.startswith(prompt):
            text = text[len(prompt):]

        return " ".join(text.split()).strip()


    def _build_generator_prompt(
        self,
        generator: TextGenerationPipeline
    ) -> str:
        """
        Derive a simple prompt for the model, preferring its BOS token.
        """
        bos = getattr(generator.tokenizer, "bos_token", None)
        if bos:
            return bos

        return random.choice(["The", "A", "One", "This"]) + " "


    @staticmethod
    def _trim_generated_text(text: str, limit: int) -> str:
        """
        Trim generated text to the configured character limit with sentence awareness.
        """
        if len(text) <= limit:
            return text

        truncated = text[:limit]
        last_sentence_end = max(
            truncated.rfind("."),
            truncated.rfind("!"),
            truncated.rfind("?")
        )
        if last_sentence_end >= limit // 2:
            truncated = truncated[:last_sentence_end + 1]

        return truncated.strip()


    def _format_target_text(self, lines: List[str]) -> str:
        """
        Wrap target text lines to the configured width without splitting words.
        """
        wrapper = textwrap.TextWrapper(
            width=TARGET_TEXT_LINE_LENGTH,
            expand_tabs=True,
            replace_whitespace=False,
            drop_whitespace=True,
            break_long_words=False,
            break_on_hyphens=False
        )
        formatted_lines: List[str] = []

        for line in lines:
            stripped_line = line.rstrip()
            if stripped_line == "":
                formatted_lines.append("")
                continue

            wrapped_line = wrapper.wrap(stripped_line)
            if not wrapped_line:
                formatted_lines.append("")
                continue

            formatted_lines.extend(part.rstrip() for part in wrapped_line)

        return "\n".join(formatted_lines)


    def _apply_loaded_text(self) -> None:
        """
        Display the selected text and reset the typing session.
        """
        normalized_lines = [
            line.rstrip()
            for line in self.selected_text.splitlines()
        ]
        self.target_text = self._format_target_text(normalized_lines)

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        self.display_text.insert("1.0", self.target_text)
        self.display_text.configure(state="disabled")

        self.info_label.configure(
            text="Start typing in the input area. WPM starts with the "
            "first key."
        )

        self.reset_session(clear_display=False)


    def reset_session(
        self,
        clear_display: bool = False,
        exit_letter_mode: bool = True,
        exit_number_mode: bool = True,
        exit_special_mode: bool = True
    ) -> None:
        """
        Reset timing and input state for a new typing session.

        :param clear_display: Whether the target text display should be cleared
        :param exit_letter_mode: Whether letter mode should be deactivated
        :param exit_number_mode: Whether number mode should be deactivated
        :param exit_special_mode: Whether special mode should be deactivated
        """
        if clear_display:
            self.display_text.configure(state="normal")
            self.display_text.delete("1.0", tk.END)
            self.display_text.configure(state="disabled")
            self.selected_text = ""
            self.target_text = ""

        self.input_text.delete("1.0", tk.END)
        self.input_text.tag_remove("error", "1.0", tk.END)

        self.start_time = None
        self.finished = False
        self.error_count = 0
        self.correct_count = 0
        self.previous_text = ""
        self.sudden_death_failure_triggered = False
        self.letter_errors = 0
        self.letter_correct_letters = 0
        self.letter_previous_text = ""
        self.number_errors = 0
        self.number_correct_digits = 0
        self.special_errors = 0
        self.special_correct_chars = 0

        if exit_letter_mode:
            self.is_letter_mode = False
            self.letter_sequence = []
            self.letter_index = 0
            self.letter_total_letters = 0

        if exit_number_mode:
            self.is_number_mode = False
            self.number_sequence = []
            self.number_index = 0
            self.number_total_digits = 0

        if exit_special_mode:
            self.is_special_mode = False
            self.special_sequence = []
            self.special_index = 0
            self.special_total_chars = 0

        if exit_letter_mode and exit_number_mode and exit_special_mode:
            self.last_session_mode = "typing"

        self.wpm_label.configure(
            text="Time: 0.0 s  |  WPM: 0.0  |  Errors: 0  |  Error %: 0.0"
        )

        if self.update_job_id is not None:
            self.master.after_cancel(self.update_job_id)
            self.update_job_id = None


    def handle_reset_button(self) -> None:
        """
        Reset or restart the currently active training mode.
        """
        if self.is_letter_mode or self.last_session_mode == "letter":
            self.start_letter_mode()
            return

        if self.is_special_mode or self.last_session_mode == "special":
            self.start_special_mode()
            return

        if self.is_number_mode or self.last_session_mode == "number":
            self.start_number_mode()
            return

        self.reset_session()


    def start_letter_mode(self) -> None:
        """
        Activate the single letter training mode with a new random sequence.
        """
        self.reset_session(clear_display=True)
        self.is_letter_mode = True
        self.letter_sequence = []
        self.letter_index = 0
        self.letter_total_letters = 0
        self._extend_letter_sequence()
        self.letter_errors = 0
        self.letter_correct_letters = 0
        self.start_time = None
        if self.is_sudden_death_active():
            info_text = (
                "Sudden death letter mode: random letters until the first mistake."
            )
        else:
            info_text = (
                "Letter mode: random letters (upper/lower). Progress 0/100."
            )
        self.info_label.configure(text=info_text)
        self._update_letter_display()
        self.update_letter_status_label()
        self.last_session_mode = "letter"

    def _extend_letter_sequence(self, chunk_size: int = LETTER_SEQUENCE_LENGTH) -> None:
        """
        Append additional random letters, keeping the no-repeat constraint intact.
        """
        if chunk_size <= 0:
            return
        previous_lower = (
            self.letter_sequence[-1].lower() if self.letter_sequence else ""
        )
        target_length = len(self.letter_sequence) + chunk_size
        while len(self.letter_sequence) < target_length:
            candidate = random.choice(LETTER_MODE_CHARACTERS)
            if previous_lower and candidate.lower() == previous_lower:
                continue
            self.letter_sequence.append(candidate)
            previous_lower = candidate.lower()
        self.letter_total_letters = len(self.letter_sequence)


    def handle_letter_mode_keypress(self, event: tk.Event) -> None:
        """
        Handle key press events while the letter mode is active.
        """
        if not self.is_letter_mode:
            return

        if self.letter_index >= self.letter_total_letters:
            return

        if self.start_time is None and len(event.char) == 1 and event.char.isprintable():
            self.start_time = time.time()

        # Ensure we react after Tk has updated the text widget.
        self.master.after_idle(self._process_letter_mode_input)


    def _process_letter_mode_input(self) -> None:
        """
        Evaluate the current text widget contents for the letter mode.
        """
        if not self.is_letter_mode:
            return

        if self.letter_index >= self.letter_total_letters:
            return

        typed_text = self.input_text.get("1.0", "end-1c").replace("\n", "")

        if typed_text == "":
            self.input_text.tag_remove("error", "1.0", tk.END)
            self.update_letter_status_label()
            return

        if len(typed_text) > 1:
            typed_text = typed_text[-1]
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", typed_text)

        current_char = typed_text
        target_letter = self.letter_sequence[self.letter_index]

        if current_char == target_letter:
            self.letter_correct_letters += 1
            self.letter_index += 1
            self.input_text.delete("1.0", tk.END)
            if self.letter_index >= self.letter_total_letters:
                if self.is_sudden_death_active():
                    self._extend_letter_sequence()
                    self._update_letter_display()
                    self.update_letter_status_label()
                else:
                    self.finish_letter_mode_session(
                        sudden_death=self.is_sudden_death_active()
                    )
            else:
                self._update_letter_display()
                self.update_letter_status_label()
            return

        self.letter_errors += 1
        if self.is_sudden_death_active():
            self.finish_letter_mode_session(sudden_death=True)
        else:
            self.input_text.delete("1.0", tk.END)
            self.update_letter_status_label()


    def _update_letter_display(self) -> None:
        """
        Show the current target letter inside the display text widget.
        """
        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)

        if self.is_letter_mode and self.letter_index < self.letter_total_letters:
            next_letter = self.letter_sequence[self.letter_index]
            letter_type = "(uppercase letter)" if next_letter.isupper() else ""
            self.display_text.insert(
                "1.0",
                f"{next_letter}\n{letter_type.upper()}"
            )
            if self.is_sudden_death_active():
                progress = (
                    "Sudden death letter mode: type the letter shown "
                    f"(streak {self.letter_index})"
                )
            else:
                progress = (
                    f"Letter mode: type the {letter_type} letter shown "
                    f"({self.letter_index}/{self.letter_total_letters})"
                )
            self.info_label.configure(text=progress)
        else:
            self.info_label.configure(
                text="Letter mode: No active letter. Click the button to start."
            )

        self.display_text.configure(state="disabled")


    def update_letter_status_label(self) -> None:
        """
        Update the shared WPM label with letter mode specific information.
        """
        if not self.is_letter_mode:
            return

        elapsed_seconds = 0.0
        letters_per_minute = 0.0

        if self.start_time is not None:
            elapsed_seconds = max(time.time() - self.start_time, 0.0001)
            elapsed_minutes = elapsed_seconds / 60.0
            if elapsed_minutes > 0.0:
                letters_per_minute = self.letter_correct_letters / elapsed_minutes

        if self.is_sudden_death_active():
            progress = f"{self.letter_correct_letters} correct (no limit)"
        else:
            progress = f"{self.letter_correct_letters}/{self.letter_total_letters}"

        self.wpm_label.configure(
            text=(
                f"Letter mode  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Letters/min: {letters_per_minute:.1f}  |  "
                f"Progress: {progress}  |  "
                f"Errors: {self.letter_errors}"
            )
        )


    def finish_letter_mode_session(self, sudden_death: bool = False) -> None:
        """
        Finalize the letter mode session and store statistics.
        """
        if not self.is_letter_mode:
            return

        elapsed_seconds = 0.0
        letters_per_minute = 0.0
        if self.start_time is not None:
            elapsed_seconds = max(time.time() - self.start_time, 0.0001)
            elapsed_minutes = elapsed_seconds / 60.0
            if elapsed_minutes > 0.0:
                letters_per_minute = self.letter_correct_letters / elapsed_minutes

        completed_sequence = self.letter_index >= self.letter_total_letters

        if sudden_death:
            correct_letters = self.letter_correct_letters
            self.save_sudden_death_letter_result(
                letters_per_minute,
                correct_letters,
                elapsed_seconds,
                completed=completed_sequence,
                is_training_run=self.training_run_var.get()
            )
            if completed_sequence:
                display_message = (
                    "Sudden death letter mode complete. "
                    "Click 'Letter mode' to start again."
                )
                info_message = (
                    "Sudden death letter mode complete. Start a new run to continue."
                )
                summary = (
                    f"Sudden death letter complete  |  Time: {elapsed_seconds:.1f} s  |  "
                    f"Letters/min: {letters_per_minute:.1f}  |  "
                    f"Correct letters: {correct_letters}"
                )
            else:
                display_message = (
                    f"Sudden death failed after {correct_letters} letters. "
                    "Click 'Letter mode' to try again."
                )
                info_message = (
                    "Sudden death letter mode failed. Start a new run to retry."
                )
                summary = (
                    f"Sudden death letter failed  |  Time: {elapsed_seconds:.1f} s  |  "
                    f"Letters/min: {letters_per_minute:.1f}  |  "
                    f"Correct letters: {correct_letters}"
                )
        else:
            total_letters = max(self.letter_total_letters, 1)
            error_percentage = (self.letter_errors / total_letters) * 100.0
            self.save_letter_result(
                letters_per_minute,
                error_percentage,
                elapsed_seconds,
                self.training_run_var.get()
            )
            display_message = (
                "Letter mode finished. Click 'Letter mode' to start again."
            )
            info_message = (
                "Letter mode finished. Start a new run via the Letter mode button."
            )
            summary = (
                f"Letter mode complete  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Letters/min: {letters_per_minute:.1f}  |  "
                f"Errors: {self.letter_errors}  |  "
                f"Error %: {error_percentage:.1f}"
            )

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        self.display_text.insert("1.0", display_message)
        self.display_text.configure(state="disabled")

        self.info_label.configure(text=info_message)
        self.wpm_label.configure(text=summary)

        self.input_text.delete("1.0", tk.END)
        self.is_letter_mode = False
        self.start_time = None
        self.letter_sequence = []
        self.letter_index = 0
        self.letter_total_letters = 0
        self.letter_errors = 0
        self.letter_correct_letters = 0
        self.last_session_mode = "letter"


    def start_special_mode(self) -> None:
        """
        Start the special character training mode with random punctuation.
        """
        self.reset_session(clear_display=True)
        self.is_special_mode = True
        self.special_sequence = []
        self.special_index = 0
        self.special_total_chars = 0
        self._extend_special_sequence()
        self.special_errors = 0
        self.special_correct_chars = 0
        self.start_time = None
        if self.is_sudden_death_active():
            info_text = (
                "Sudden death special mode: punctuation practice until the first error."
            )
        else:
            info_text = (
                "Special character mode: focus on punctuation and symbols. Progress 0/100."
            )
        self.info_label.configure(text=info_text)
        self._update_special_display()
        self.update_special_status_label()
        self.last_session_mode = "special"

    def _extend_special_sequence(self, chunk_size: int = SPECIAL_SEQUENCE_LENGTH) -> None:
        """
        Append additional random special characters without consecutive duplicates.
        """
        if chunk_size <= 0:
            return
        previous_char = self.special_sequence[-1] if self.special_sequence else ""
        target_length = len(self.special_sequence) + chunk_size
        while len(self.special_sequence) < target_length:
            candidate = random.choice(SPECIAL_MODE_CHARACTERS)
            if previous_char and candidate == previous_char:
                continue
            self.special_sequence.append(candidate)
            previous_char = candidate
        self.special_total_chars = len(self.special_sequence)

    def handle_special_mode_keypress(self, event: tk.Event) -> None:
        """
        Handle key press events while the special character mode is active.
        """
        if not self.is_special_mode:
            return

        if self.special_index >= self.special_total_chars:
            return

        if self.start_time is None and len(event.char) == 1 and event.char.isprintable():
            self.start_time = time.time()

        self.master.after_idle(self._process_special_mode_input)

    def _process_special_mode_input(self) -> None:
        """
        Evaluate the current text widget contents for the special character mode.
        """
        if not self.is_special_mode:
            return

        if self.special_index >= self.special_total_chars:
            return

        typed_text = self.input_text.get("1.0", "end-1c").replace("\n", "")

        if typed_text == "":
            self.input_text.tag_remove("error", "1.0", tk.END)
            self.update_special_status_label()
            return

        if len(typed_text) > 1:
            typed_text = typed_text[-1]
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", typed_text)

        current_char = typed_text
        target_symbol = self.special_sequence[self.special_index]

        if current_char == target_symbol:
            self.special_correct_chars += 1
            self.special_index += 1
            self.input_text.delete("1.0", tk.END)
            if self.special_index >= self.special_total_chars:
                if self.is_sudden_death_active():
                    self._extend_special_sequence()
                    self._update_special_display()
                    self.update_special_status_label()
                else:
                    self.finish_special_mode_session(
                        sudden_death=self.is_sudden_death_active()
                    )
            else:
                self._update_special_display()
                self.update_special_status_label()
            return

        self.special_errors += 1
        if self.is_sudden_death_active():
            self.finish_special_mode_session(sudden_death=True)
        else:
            self.input_text.delete("1.0", tk.END)
            self.update_special_status_label()

    def _update_special_display(self) -> None:
        """
        Show the current target symbol inside the display text widget.
        """
        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)

        if self.is_special_mode and self.special_index < self.special_total_chars:
            next_symbol = self.special_sequence[self.special_index]
            self.display_text.insert(
                "1.0",
                f"{next_symbol}\n(SYMBOL)"
            )
            if self.is_sudden_death_active():
                progress = (
                    "Sudden death special mode: type the symbol shown "
                    f"(streak {self.special_index})"
                )
            else:
                progress = (
                    "Special character mode: type the symbol shown "
                    f"({self.special_index}/{self.special_total_chars})"
                )
            self.info_label.configure(text=progress)
        else:
            self.info_label.configure(
                text="Special character mode: No active symbol. Click the button to start."
            )

        self.display_text.configure(state="disabled")

    def update_special_status_label(self) -> None:
        """
        Update the shared WPM label with special mode specific information.
        """
        if not self.is_special_mode:
            return

        elapsed_seconds = 0.0
        symbols_per_minute = 0.0

        if self.start_time is not None:
            elapsed_seconds = max(time.time() - self.start_time, 0.0001)
            elapsed_minutes = elapsed_seconds / 60.0
            if elapsed_minutes > 0.0:
                symbols_per_minute = self.special_correct_chars / elapsed_minutes

        if self.is_sudden_death_active():
            progress = f"{self.special_correct_chars} correct (no limit)"
        else:
            progress = f"{self.special_correct_chars}/{self.special_total_chars}"

        self.wpm_label.configure(
            text=(
                f"Special char mode  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Symbols/min: {symbols_per_minute:.1f}  |  "
                f"Progress: {progress}  |  "
                f"Errors: {self.special_errors}"
            )
        )

    def finish_special_mode_session(self, sudden_death: bool = False) -> None:
        """
        Finalize the special character mode session and persist statistics.
        """
        if not self.is_special_mode:
            return

        elapsed_seconds = 0.0
        symbols_per_minute = 0.0
        if self.start_time is not None:
            elapsed_seconds = max(time.time() - self.start_time, 0.0001)
            elapsed_minutes = elapsed_seconds / 60.0
            if elapsed_minutes > 0.0:
                symbols_per_minute = self.special_correct_chars / elapsed_minutes

        completed_sequence = self.special_index >= self.special_total_chars

        if sudden_death:
            correct_symbols = self.special_correct_chars
            self.save_sudden_death_special_result(
                symbols_per_minute,
                correct_symbols,
                elapsed_seconds,
                completed=completed_sequence,
                is_training_run=self.training_run_var.get()
            )
            if completed_sequence:
                display_message = (
                    "Sudden death special mode complete. "
                    "Click 'Special char mode' to start again."
                )
                info_message = (
                    "Sudden death special mode complete. Start a new run to continue."
                )
                summary = (
                    f"Sudden death special complete  |  Time: {elapsed_seconds:.1f} s  |  "
                    f"Symbols/min: {symbols_per_minute:.1f}  |  "
                    f"Correct symbols: {correct_symbols}"
                )
            else:
                display_message = (
                    f"Sudden death failed after {correct_symbols} symbols. "
                    "Click 'Special char mode' to try again."
                )
                info_message = (
                    "Sudden death special mode failed. Start a new run to retry."
                )
                summary = (
                    f"Sudden death special failed  |  Time: {elapsed_seconds:.1f} s  |  "
                    f"Symbols/min: {symbols_per_minute:.1f}  |  "
                    f"Correct symbols: {correct_symbols}"
                )
        else:
            total_symbols = max(self.special_total_chars, 1)
            error_percentage = (self.special_errors / total_symbols) * 100.0
            self.save_special_result(
                symbols_per_minute,
                error_percentage,
                elapsed_seconds,
                self.training_run_var.get()
            )
            display_message = (
                "Special character mode finished. Click 'Special char mode' to start again."
            )
            info_message = (
                "Special character mode finished. Start a new run via the Special char mode button."
            )
            summary = (
                f"Special mode complete  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Symbols/min: {symbols_per_minute:.1f}  |  "
                f"Errors: {self.special_errors}  |  "
                f"Error %: {error_percentage:.1f}"
            )

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        self.display_text.insert("1.0", display_message)
        self.display_text.configure(state="disabled")

        self.info_label.configure(text=info_message)
        self.wpm_label.configure(text=summary)

        self.input_text.delete("1.0", tk.END)
        self.is_special_mode = False
        self.start_time = None
        self.special_sequence = []
        self.special_index = 0
        self.special_total_chars = 0
        self.special_errors = 0
        self.special_correct_chars = 0
        self.last_session_mode = "special"


    def start_number_mode(self) -> None:
        """
        Activate the numeric keypad training mode with a random digit sequence.
        """
        self.reset_session(clear_display=True)
        self.is_number_mode = True
        self.number_sequence = []
        self.number_index = 0
        self.number_total_digits = 0
        self._extend_number_sequence()
        self.number_errors = 0
        self.number_correct_digits = 0
        self.start_time = None
        if self.is_sudden_death_active():
            info_text = (
                "Sudden death number mode: keep typing digits until the first error."
            )
        else:
            info_text = (
                "Number mode: type digits with the numeric keypad. Progress 0/100."
            )
        self.info_label.configure(text=info_text)
        self._update_number_display()
        self.update_number_status_label()
        self.last_session_mode = "number"

    def _extend_number_sequence(self, chunk_size: int = NUMBER_SEQUENCE_LENGTH) -> None:
        """
        Append additional random digits while avoiding immediate repeats.
        """
        if chunk_size <= 0:
            return
        previous_digit = self.number_sequence[-1] if self.number_sequence else ""
        target_length = len(self.number_sequence) + chunk_size
        while len(self.number_sequence) < target_length:
            candidate = random.choice(string.digits)
            if previous_digit and candidate == previous_digit:
                continue
            self.number_sequence.append(candidate)
            previous_digit = candidate
        self.number_total_digits = len(self.number_sequence)


    def handle_number_mode_keypress(self, event: tk.Event) -> None:
        """
        Handle key press events while the number mode is active.
        """
        if not self.is_number_mode:
            return

        if self.number_index >= self.number_total_digits:
            return

        if self.start_time is None and len(event.char) == 1 and event.char.isprintable():
            self.start_time = time.time()

        self.master.after_idle(self._process_number_mode_input)


    def _process_number_mode_input(self) -> None:
        """
        Evaluate the current text widget contents for the number mode.
        """
        if not self.is_number_mode:
            return

        if self.number_index >= self.number_total_digits:
            return

        typed_text = self.input_text.get("1.0", "end-1c").replace("\n", "")

        if typed_text == "":
            self.input_text.tag_remove("error", "1.0", tk.END)
            self.update_number_status_label()
            return

        if len(typed_text) > 1:
            typed_text = typed_text[-1]
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", typed_text)

        current_char = typed_text
        target_digit = self.number_sequence[self.number_index]

        if current_char == target_digit:
            self.number_correct_digits += 1
            self.number_index += 1
            self.input_text.delete("1.0", tk.END)
            if self.number_index >= self.number_total_digits:
                if self.is_sudden_death_active():
                    self._extend_number_sequence()
                    self._update_number_display()
                    self.update_number_status_label()
                else:
                    self.finish_number_mode_session(
                        sudden_death=self.is_sudden_death_active()
                    )
            else:
                self._update_number_display()
                self.update_number_status_label()
            return

        self.number_errors += 1
        if self.is_sudden_death_active():
            self.finish_number_mode_session(sudden_death=True)
        else:
            self.input_text.delete("1.0", tk.END)
            self.update_number_status_label()


    def _update_number_display(self) -> None:
        """
        Show the current target digit inside the display text widget.
        """
        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)

        if self.is_number_mode and self.number_index < self.number_total_digits:
            next_digit = self.number_sequence[self.number_index]
            self.display_text.insert(
                "1.0",
                f"{next_digit}\n(DIGIT)"
            )
            if self.is_sudden_death_active():
                progress = (
                    "Sudden death number mode: type the digit shown "
                    f"(streak {self.number_index})"
                )
            else:
                progress = (
                    f"Number mode: type the digit shown "
                    f"({self.number_index}/{self.number_total_digits})"
                )
            self.info_label.configure(text=progress)
        else:
            self.info_label.configure(
                text="Number mode: No active digit. Click the button to start."
            )

        self.display_text.configure(state="disabled")


    def update_number_status_label(self) -> None:
        """
        Update the shared WPM label with number mode specific information.
        """
        if not self.is_number_mode:
            return

        elapsed_seconds = 0.0
        digits_per_minute = 0.0

        if self.start_time is not None:
            elapsed_seconds = max(time.time() - self.start_time, 0.0001)
            elapsed_minutes = elapsed_seconds / 60.0
            if elapsed_minutes > 0.0:
                digits_per_minute = self.number_correct_digits / elapsed_minutes

        if self.is_sudden_death_active():
            progress = f"{self.number_correct_digits} correct (no limit)"
        else:
            progress = f"{self.number_correct_digits}/{self.number_total_digits}"

        self.wpm_label.configure(
            text=(
                f"Number mode  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Digits/min: {digits_per_minute:.1f}  |  "
                f"Progress: {progress}  |  "
                f"Errors: {self.number_errors}"
            )
        )


    def finish_number_mode_session(self, sudden_death: bool = False) -> None:
        """
        Finalize the number mode session and store statistics.
        """
        if not self.is_number_mode:
            return

        elapsed_seconds = 0.0
        digits_per_minute = 0.0
        if self.start_time is not None:
            elapsed_seconds = max(time.time() - self.start_time, 0.0001)
            elapsed_minutes = elapsed_seconds / 60.0
            if elapsed_minutes > 0.0:
                digits_per_minute = self.number_correct_digits / elapsed_minutes

        completed_sequence = self.number_index >= self.number_total_digits

        if sudden_death:
            correct_digits = self.number_correct_digits
            self.save_sudden_death_number_result(
                digits_per_minute,
                correct_digits,
                elapsed_seconds,
                completed=completed_sequence,
                is_training_run=self.training_run_var.get()
            )
            if completed_sequence:
                display_message = (
                    "Sudden death number mode complete. "
                    "Click 'Number mode' to start again."
                )
                info_message = (
                    "Sudden death number mode complete. Start a new run to continue."
                )
                summary = (
                    f"Sudden death number complete  |  Time: {elapsed_seconds:.1f} s  |  "
                    f"Digits/min: {digits_per_minute:.1f}  |  "
                    f"Correct digits: {correct_digits}"
                )
            else:
                display_message = (
                    f"Sudden death failed after {correct_digits} digits. "
                    "Click 'Number mode' to try again."
                )
                info_message = (
                    "Sudden death number mode failed. Start a new run to retry."
                )
                summary = (
                    f"Sudden death number failed  |  Time: {elapsed_seconds:.1f} s  |  "
                    f"Digits/min: {digits_per_minute:.1f}  |  "
                    f"Correct digits: {correct_digits}"
                )
        else:
            total_digits = max(self.number_total_digits, 1)
            error_percentage = (self.number_errors / total_digits) * 100.0
            self.save_number_result(
                digits_per_minute,
                error_percentage,
                elapsed_seconds,
                self.training_run_var.get()
            )
            display_message = (
                "Number mode finished. Click 'Number mode' to start again."
            )
            info_message = (
                "Number mode finished. Start a new run via the Number mode button."
            )
            summary = (
                f"Number mode complete  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Digits/min: {digits_per_minute:.1f}  |  "
                f"Errors: {self.number_errors}  |  "
                f"Error %: {error_percentage:.1f}"
            )

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        self.display_text.insert("1.0", display_message)
        self.display_text.configure(state="disabled")

        self.info_label.configure(text=info_message)
        self.wpm_label.configure(text=summary)

        self.input_text.delete("1.0", tk.END)
        self.is_number_mode = False
        self.start_time = None
        self.number_sequence = []
        self.number_index = 0
        self.number_total_digits = 0
        self.number_errors = 0
        self.number_correct_digits = 0
        self.last_session_mode = "number"


    def on_key_press(self, event: tk.Event) -> None:
        """
        Handle key presses in the input box and start timing if needed.

        The function starts the timer on the first non control key and triggers
        updates of WPM and error highlighting. If the text is already finished,
        additional key presses do not change the statistics.
        """
        if self.is_letter_mode:
            self.handle_letter_mode_keypress(event)
            return

        if self.is_special_mode:
            self.handle_special_mode_keypress(event)
            return

        if self.is_number_mode:
            self.handle_number_mode_keypress(event)
            return

        if self.target_text == "":
            self.info_label.configure(
                text="Please select and load a text before typing."
            )
            return

        if self.finished:
            return

        if self.start_time is None:
            if len(event.char) == 0:
                return
            self.start_time = time.time()
            self.schedule_periodic_update()

        self.update_typing_state()


    def schedule_periodic_update(self) -> None:
        """
        Schedule periodic updates of WPM and error highlighting.
        """
        if self.finished:
            return

        self.update_typing_state()
        self.update_job_id = self.master.after(
            200,
            self.schedule_periodic_update,
        )


    def update_typing_state(self) -> None:
        """
        Update WPM, highlight errors, and detect completion of the text.
        """
        if self.finished:
            return

        typed_text = self.input_text.get("1.0", "end-1c")

        # First update cumulative error counter based on the change.
        self._update_error_counter(self.previous_text, typed_text)

        # Then update current error highlighting and correct-count.
        first_error_index = self.highlight_errors(typed_text)

        if (
            self.is_sudden_death_active()
            and first_error_index is not None
        ):
            self.handle_sudden_death_text_failure(first_error_index)
            return

        # Update statistics row and check for completion.
        self.update_wpm(typed_text)
        self.check_completion(typed_text)

        # Store current text for next comparison.
        self.previous_text = typed_text


    def _update_error_counter(self, previous: str, current: str) -> None:
        """
        Update the cumulative error counter based on the change in text.

        An error is counted whenever a new character appears or a character
        changes and the resulting character does not match the target text
        at that position.
        """
        # Fast path when nothing changed
        if previous == current:
            return

        # Determine the common prefix where everything is identical
        prefix_len = 0
        max_prefix = min(len(previous), len(current))
        while (
            prefix_len < max_prefix
            and previous[prefix_len] == current[prefix_len]
        ):
            prefix_len += 1

        # Determine the common suffix (after the prefix) that is also identical
        prev_suffix = len(previous)
        curr_suffix = len(current)
        while (
            prev_suffix > prefix_len
            and curr_suffix > prefix_len
            and previous[prev_suffix - 1] == current[curr_suffix - 1]
        ):
            prev_suffix -= 1
            curr_suffix -= 1

        # Only examine the truly new/changed characters in the current text
        for index in range(prefix_len, curr_suffix):
            new_char = current[index]
            if index >= len(self.target_text):
                self.error_count += 1
            elif new_char != self.target_text[index]:
                self.error_count += 1


    def highlight_errors(self, typed_text: str) -> int | None:
        """
        Highlight incorrect characters in the input text.

        A character is considered incorrect if it does not match the target
        text at the same position. Additional characters beyond the length of
        the target are also considered incorrect. This function also updates
        the current number of correct characters.
        """
        self.input_text.tag_remove("error", "1.0", tk.END)

        correct = 0
        first_error_index: int | None = None

        for index, char in enumerate(typed_text):
            if index >= len(self.target_text):
                start = f"1.0 + {index} chars"
                end = f"1.0 + {index + 1} chars"
                self.input_text.tag_add("error", start, end)
                if first_error_index is None:
                    first_error_index = index
                continue

            if char != self.target_text[index]:
                start = f"1.0 + {index} chars"
                end = f"1.0 + {index + 1} chars"
                self.input_text.tag_add("error", start, end)
                if first_error_index is None:
                    first_error_index = index
            else:
                correct += 1

        self.correct_count = correct
        return first_error_index

    def handle_sudden_death_text_failure(self, failure_index: int) -> None:
        """
        Finalize a typing session when sudden death detects a mistake.
        """
        if self.finished or self.sudden_death_failure_triggered:
            return

        self.sudden_death_failure_triggered = True
        self.finished = True

        if self.update_job_id is not None:
            self.master.after_cancel(self.update_job_id)
            self.update_job_id = None

        safe_index = max(0, min(failure_index, len(self.target_text)))
        elapsed_seconds = 0.0
        wpm = 0.0
        if self.start_time is not None:
            elapsed_seconds = max(time.time() - self.start_time, 0.0001)
            elapsed_minutes = elapsed_seconds / 60.0
            correct_segment = self.target_text[:safe_index]
            words = len(correct_segment.split())
            if elapsed_minutes > 0.0:
                wpm = words / elapsed_minutes
        else:
            correct_segment = self.target_text[:safe_index]

        self.save_sudden_death_wpm_result(
            wpm,
            safe_index,
            elapsed_seconds,
            completed=False,
            is_training_run=self.training_run_var.get()
        )

        self.info_label.configure(
            text=(
                f"Sudden death failed after {safe_index} characters. "
                "Load a text to try again."
            )
        )
        self.wpm_label.configure(
            text=(
                f"Sudden death  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Correct chars: {safe_index}  |  WPM: {wpm:.1f}"
            )
        )


    def update_wpm(self, typed_text: str) -> None:
        if self.start_time is None:
            self.wpm_label.configure(
                text="Time: 0.0 s  |  WPM: 0.0  |  Errors: 0  |  Error %: 0.0"
            )
            return

        elapsed_seconds = max(time.time() - self.start_time, 0.0001)
        elapsed_minutes = elapsed_seconds / 60.0

        words = len(typed_text.split())
        wpm = words / elapsed_minutes if elapsed_minutes > 0.0 else 0.0

        errors = self.error_count
        correct = self.correct_count

        total_typed = errors + correct
        if total_typed <= 0:
            error_percentage = 0.0
        else:
            error_percentage = (errors / total_typed) * 100.0

        self.wpm_label.configure(
            text=(
                f"Time: {elapsed_seconds:.1f} s  |  "
                f"WPM: {wpm:.1f}  |  "
                f"Errors: {errors}  |  "
                f"Error %: {error_percentage:.1f}"
            )
        )


    def check_completion(self, typed_text: str) -> None:
        """
        Check whether the user has fully and correctly typed the target text.

        Once the text is completed, the timer is stopped and the result is
        saved to the statistics file.
        """
        if typed_text != self.target_text:
            return

        if self.start_time is None:
            return

        self.finished = True

        if self.update_job_id is not None:
            self.master.after_cancel(self.update_job_id)
            self.update_job_id = None

        words = len(typed_text.split())
        elapsed_seconds = max(time.time() - self.start_time, 0.0001)
        elapsed_minutes = elapsed_seconds / 60.0
        wpm = words / elapsed_minutes if elapsed_minutes > 0.0 else 0.0

        errors = self.error_count
        correct = self.correct_count
        total = errors + correct
        if total <= 0:
            error_percentage = 0.0
        else:
            error_percentage = (errors / total) * 100.0

        if self.is_sudden_death_active():
            self.save_sudden_death_wpm_result(
                wpm,
                len(self.target_text),
                elapsed_seconds,
                completed=True,
                is_training_run=self.training_run_var.get()
            )
            self.info_label.configure(
                text="Sudden death complete. Start another run when ready."
            )
            self.wpm_label.configure(
                text=(
                    f"Sudden death  |  Time: {elapsed_seconds:.1f} s  |  "
                    f"WPM: {wpm:.1f}  |  Correct chars: {len(self.target_text)}"
                )
            )
        else:
            self.save_wpm_result(
                wpm,
                error_percentage,
                elapsed_seconds,
                self.training_run_var.get()
            )


    def save_wpm_result(
        self,
        wpm: float,
        error_percentage: float,
        duration_seconds: float,
        is_training_run: bool
    ) -> None:
        """
        Append the given WPM value and error rate to the statistics file.

        The values are appended as a simple CSV that also stores whether the
        session was marked as a training run.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        training_flag = "1" if is_training_run else "0"
        line = (
            f"{timestamp};{wpm:.3f};{error_percentage:.3f};"
            f"{duration_seconds:.3f};{training_flag}\n"
        )
        ensure_stats_file_header(self.stats_file_path, STATS_FILE_HEADER)
        with self.stats_file_path.open("a", encoding="utf-8") as stats_file:
            stats_file.write(line)

    def save_sudden_death_wpm_result(
        self,
        wpm: float,
        correct_characters: int,
        duration_seconds: float,
        completed: bool,
        is_training_run: bool
    ) -> None:
        """
        Store sudden death typing results with the number of correct characters.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        completed_flag = "1" if completed else "0"
        training_flag = "1" if is_training_run else "0"
        line = (
            f"{timestamp};{wpm:.3f};{correct_characters};"
            f"{duration_seconds:.3f};{completed_flag};{training_flag}\n"
        )
        ensure_stats_file_header(
            self.sudden_death_typing_stats_file_path,
            SUDDEN_DEATH_TYPING_STATS_FILE_HEADER
        )
        with self.sudden_death_typing_stats_file_path.open(
            "a",
            encoding="utf-8"
        ) as stats_file:
            stats_file.write(line)


    def save_letter_result(
        self,
        letters_per_minute: float,
        error_percentage: float,
        duration_seconds: float,
        is_training_run: bool
    ) -> None:
        """
        Append the letter mode statistics to the dedicated CSV file.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        training_flag = "1" if is_training_run else "0"
        line = (
            f"{timestamp};{letters_per_minute:.3f};"
            f"{error_percentage:.3f};{duration_seconds:.3f};"
            f"{training_flag}\n"
        )
        ensure_stats_file_header(
            self.letter_stats_file_path,
            LETTER_STATS_FILE_HEADER
        )
        with self.letter_stats_file_path.open("a", encoding="utf-8") as file:
            file.write(line)

    def save_sudden_death_letter_result(
        self,
        letters_per_minute: float,
        correct_letters: int,
        duration_seconds: float,
        completed: bool,
        is_training_run: bool
    ) -> None:
        """
        Store sudden death letter mode results.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        completed_flag = "1" if completed else "0"
        training_flag = "1" if is_training_run else "0"
        line = (
            f"{timestamp};{letters_per_minute:.3f};{correct_letters};"
            f"{duration_seconds:.3f};{completed_flag};{training_flag}\n"
        )
        ensure_stats_file_header(
            self.sudden_death_letter_stats_file_path,
            SUDDEN_DEATH_LETTER_STATS_FILE_HEADER
        )
        with self.sudden_death_letter_stats_file_path.open(
            "a",
            encoding="utf-8"
        ) as file:
            file.write(line)


    def save_special_result(
        self,
        symbols_per_minute: float,
        error_percentage: float,
        duration_seconds: float,
        is_training_run: bool
    ) -> None:
        """
        Append the special character mode statistics to the dedicated CSV file.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        training_flag = "1" if is_training_run else "0"
        line = (
            f"{timestamp};{symbols_per_minute:.3f};"
            f"{error_percentage:.3f};{duration_seconds:.3f};"
            f"{training_flag}\n"
        )
        ensure_stats_file_header(
            self.special_stats_file_path,
            SPECIAL_STATS_FILE_HEADER
        )
        with self.special_stats_file_path.open("a", encoding="utf-8") as file:
            file.write(line)

    def save_sudden_death_special_result(
        self,
        symbols_per_minute: float,
        correct_symbols: int,
        duration_seconds: float,
        completed: bool,
        is_training_run: bool
    ) -> None:
        """
        Store sudden death special mode results.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        completed_flag = "1" if completed else "0"
        training_flag = "1" if is_training_run else "0"
        line = (
            f"{timestamp};{symbols_per_minute:.3f};{correct_symbols};"
            f"{duration_seconds:.3f};{completed_flag};{training_flag}\n"
        )
        ensure_stats_file_header(
            self.sudden_death_special_stats_file_path,
            SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER
        )
        with self.sudden_death_special_stats_file_path.open(
            "a",
            encoding="utf-8"
        ) as file:
            file.write(line)


    def save_number_result(
        self,
        digits_per_minute: float,
        error_percentage: float,
        duration_seconds: float,
        is_training_run: bool
    ) -> None:
        """
        Append the number mode statistics to the dedicated CSV file.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        training_flag = "1" if is_training_run else "0"
        line = (
            f"{timestamp};{digits_per_minute:.3f};"
            f"{error_percentage:.3f};{duration_seconds:.3f};"
            f"{training_flag}\n"
        )
        ensure_stats_file_header(
            self.number_stats_file_path,
            NUMBER_STATS_FILE_HEADER
        )
        with self.number_stats_file_path.open("a", encoding="utf-8") as file:
            file.write(line)

    def save_sudden_death_number_result(
        self,
        digits_per_minute: float,
        correct_digits: int,
        duration_seconds: float,
        completed: bool,
        is_training_run: bool
    ) -> None:
        """
        Store sudden death number mode results.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        completed_flag = "1" if completed else "0"
        training_flag = "1" if is_training_run else "0"
        line = (
            f"{timestamp};{digits_per_minute:.3f};{correct_digits};"
            f"{duration_seconds:.3f};{completed_flag};{training_flag}\n"
        )
        ensure_stats_file_header(
            self.sudden_death_number_stats_file_path,
            SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER
        )
        with self.sudden_death_number_stats_file_path.open(
            "a",
            encoding="utf-8"
        ) as file:
            file.write(line)


    def show_result(self) -> None:
        """
        Show a simple dialog with statistics for the current session.

        If there is no valid timing or no text has been typed, a message is
        displayed informing the user.
        """
        typed_text = self.input_text.get("1.0", "end-1c").strip()
        words = len(typed_text.split())

        if self.start_time is None or words == 0:
            messagebox.showinfo(
                "Result",
                "No timing information available yet. "
                "Please type some text.",
            )
            return

        elapsed_seconds = max(time.time() - self.start_time, 0.0001)
        elapsed_minutes = elapsed_seconds / 60.0
        wpm = words / elapsed_minutes if elapsed_minutes > 0.0 else 0.0

        message = (
            f"Words typed: {words}\n"
            f"Time: {elapsed_seconds:.1f} seconds\n"
            f"Average WPM: {wpm:.1f}"
        )
        messagebox.showinfo("Result", message)

    def _show_sudden_death_stats(
        self,
        *,
        file_path: Path,
        header: str,
        mode_label: str,
        speed_label: str,
        speed_short_label: str,
        correct_label: str
    ) -> None:
        """
        Shared visualization helper for sudden death statistics across modes.
        """
        title = f"Sudden death {mode_label} statistics"
        if not file_path.exists():
            messagebox.showinfo(
                title,
                f"No sudden death {mode_label} statistics available yet. "
                "Finish at least one sudden death run."
            )
            return

        ensure_stats_file_header(
            file_path,
            header,
            create_if_missing=False
        )

        speed_values: List[float] = []
        correct_counts: List[float] = []
        daily_stats: dict = {}

        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 6:
                    continue
                is_training_run = self._parse_training_flag(parts, 5)
                if not self._should_include_training_entry(is_training_run):
                    continue
                try:
                    speed_val = float(parts[1])
                    correct_val = float(parts[2])
                except ValueError:
                    continue
                try:
                    day = datetime.strptime(
                        parts[0],
                        "%Y-%m-%d %H:%M:%S"
                    ).date()
                except ValueError:
                    day = None
                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None

                speed_values.append(speed_val)
                correct_counts.append(correct_val)
                if day is not None:
                    entry = daily_stats.setdefault(
                        day,
                        {
                            "speed_sum": 0.0,
                            "speed_count": 0,
                            "correct_sum": 0.0,
                            "correct_count": 0,
                            "duration_sum": 0.0,
                        }
                    )
                    entry["speed_sum"] += speed_val
                    entry["speed_count"] += 1
                    entry["correct_sum"] += correct_val
                    entry["correct_count"] += 1
                    if duration_val is not None:
                        entry["duration_sum"] += max(duration_val, 0.0)

        if not speed_values:
            messagebox.showinfo(
                title,
                "No statistics available for the current filter selection."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_correct: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_speed.append(stats["speed_sum"] / stats["speed_count"])
                    daily_correct.append(
                        stats["correct_sum"] / stats["correct_count"]
                    )
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_speed.append(0.0)
                    daily_correct.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_correct = fig.add_subplot(grid_spec[0, 1])
        ax_3d = fig.add_subplot(grid_spec[1, :], projection="3d")
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_speed.hist(
            speed_values,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_speed.set_title(f"{speed_label} distribution")
        ax_speed.set_xlabel(speed_label)
        ax_speed.set_ylabel("Frequency")

        if correct_counts:
            ax_correct.hist(
                correct_counts,
                bins="auto",
                color=palette["hist_correct_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_correct.set_title(f"{correct_label} distribution")
            ax_correct.set_xlabel(correct_label)
            ax_correct.set_ylabel("Frequency")
        else:
            ax_correct.set_title(f"{correct_label} distribution")
            ax_correct.text(
                0.5,
                0.5,
                "No data available",
                ha="center",
                va="center",
                transform=ax_correct.transAxes,
                color=palette["text_color"]
            )
            ax_correct.set_xticks([])
            ax_correct.set_yticks([])

        if speed_values and correct_counts:
            speed_arr = np.asarray(speed_values, dtype=float)
            correct_arr = np.asarray(correct_counts, dtype=float)
            x_edges = np.histogram_bin_edges(speed_arr, bins="auto")
            y_edges = np.histogram_bin_edges(correct_arr, bins="auto")
            hist, xedges, yedges = np.histogram2d(
                speed_arr,
                correct_arr,
                bins=[x_edges, y_edges]
            )
            x_positions = xedges[:-1]
            y_positions = yedges[:-1]
            x_sizes = np.diff(xedges)
            y_sizes = np.diff(yedges)
            xpos, ypos = np.meshgrid(
                x_positions,
                y_positions,
                indexing="ij"
            )
            dx, dy = np.meshgrid(
                x_sizes,
                y_sizes,
                indexing="ij"
            )
            xpos = xpos.ravel()
            ypos = ypos.ravel()
            dx = dx.ravel()
            dy = dy.ravel()
            dz = hist.ravel()
            nonzero = dz > 0
            xpos = xpos[nonzero]
            ypos = ypos[nonzero]
            dx = dx[nonzero]
            dy = dy[nonzero]
            dz = dz[nonzero]
            if dz.size > 0:
                ax_3d.bar3d(
                    xpos,
                    ypos,
                    np.zeros_like(dz),
                    dx,
                    dy,
                    dz,
                    shade=True,
                    color=palette["bar3d_color"]
                )
            else:
                ax_3d.text(
                    0.5,
                    0.5,
                    0.5,
                    "No combined data available",
                    ha="center",
                    va="center",
                    color=palette["text_color"]
                )
                ax_3d.set_xticks([])
                ax_3d.set_yticks([])
                ax_3d.set_zticks([])
        else:
            ax_3d.text(
                0.5,
                0.5,
                0.5,
                "No combined data available",
                ha="center",
                va="center",
                color=palette["text_color"]
            )
            ax_3d.set_xticks([])
            ax_3d.set_yticks([])
            ax_3d.set_zticks([])

        ax_3d.set_title(
            f"Joint {speed_short_label} / {correct_label.lower()} distribution"
        )
        ax_3d.set_xlabel(speed_short_label)
        ax_3d.set_ylabel(correct_label)
        ax_3d.set_zlabel("Count")

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_speed,
                width=bar_width,
                color=palette["daily_speed_color"],
                label=f"Average {speed_short_label}"
            )
            ax_time.bar(
                positions,
                daily_correct,
                width=bar_width,
                color=palette["daily_error_color"],
                label=f"Average {correct_label.lower()}"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title(
                f"Daily averages ({speed_short_label} vs {correct_label.lower()})"
            )
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title(
                f"Daily averages ({speed_short_label} vs {correct_label.lower()})"
            )
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_stats(self) -> None:
        """
        Show histograms of WPM, error percentage, and a 3D joint histogram
        in a single Matplotlib figure.

        If no statistics file exists or no valid values can be read, an
        information dialog is shown instead.
        """
        if self.is_sudden_death_active():
            self._show_sudden_death_stats(
                file_path=self.sudden_death_typing_stats_file_path,
                header=SUDDEN_DEATH_TYPING_STATS_FILE_HEADER,
                mode_label="typing",
                speed_label="Words per minute",
                speed_short_label="WPM",
                correct_label="Correct characters"
            )
            return

        if not self.stats_file_path.exists():
            messagebox.showinfo(
                "Statistics",
                "No statistics file found yet. "
                "Finish at least one session."
            )
            return

        ensure_stats_file_header(
            self.stats_file_path,
            STATS_FILE_HEADER,
            create_if_missing=False
        )

        wpm_values: List[float] = []
        error_rates: List[float] = []
        wpm_for_3d: List[float] = []
        error_for_3d: List[float] = []
        daily_stats: dict = {}

        with self.stats_file_path.open("r", encoding="utf-8") as stats_file:
            for line in stats_file:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) < 2:
                    continue
                is_training_run = self._parse_training_flag(parts, 4)
                if not self._should_include_training_entry(is_training_run):
                    continue

                try:
                    day = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S").date()
                except ValueError:
                    day = None

                try:
                    wpm_val = float(parts[1])
                except ValueError:
                    continue
                wpm_values.append(wpm_val)

                err_val: float | None = None
                if len(parts) >= 3:
                    try:
                        err_val = float(parts[2])
                    except ValueError:
                        err_val = None
                    if err_val is not None:
                        error_rates.append(err_val)
                        wpm_for_3d.append(wpm_val)
                        error_for_3d.append(err_val)

                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None

                if day is not None:
                    entry = daily_stats.setdefault(
                        day,
                        {
                            "wpm_sum": 0.0,
                            "wpm_count": 0,
                            "error_sum": 0.0,
                            "error_count": 0,
                            "duration_sum": 0.0,
                        }
                    )
                    entry["wpm_sum"] += wpm_val
                    entry["wpm_count"] += 1
                    if err_val is not None:
                        entry["error_sum"] += err_val
                        entry["error_count"] += 1
                    if duration_val is not None:
                        entry["duration_sum"] += max(duration_val, 0.0)

        if not wpm_values:
            messagebox.showinfo(
                "Statistics",
                "No statistics available for the current filter selection.",
            )
            return

        daily_dates: List[date] = []
        daily_wpm: List[float] = []
        daily_error: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_wpm.append(stats["wpm_sum"] / stats["wpm_count"])
                    if stats["error_count"] > 0:
                        daily_error.append(
                            stats["error_sum"] / stats["error_count"]
                        )
                    else:
                        daily_error.append(0.0)
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_wpm.append(0.0)
                    daily_error.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_wpm = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_3d = fig.add_subplot(grid_spec[1, :], projection="3d")
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_wpm.hist(
            wpm_values,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_wpm.set_title("WPM distribution")
        ax_wpm.set_xlabel("Words per minute")
        ax_wpm.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(
                error_rates,
                bins="auto",
                color=palette["hist_error_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_error.set_title("Error percentage distribution")
            ax_error.set_xlabel("Error percentage (%)")
            ax_error.set_ylabel("Frequency")
        else:
            ax_error.set_title("Error percentage distribution")
            ax_error.text(
                0.5,
                0.5,
                "No error-rate data available",
                ha="center",
                va="center",
                transform=ax_error.transAxes,
                color=palette["text_color"]
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        if wpm_for_3d and error_for_3d:
            wpm_arr = np.asarray(wpm_for_3d, dtype=float)
            error_arr = np.asarray(error_for_3d, dtype=float)

            x_edges = np.histogram_bin_edges(wpm_arr, bins="auto")
            y_edges = np.histogram_bin_edges(error_arr, bins="auto")

            hist, xedges, yedges = np.histogram2d(
                wpm_arr,
                error_arr,
                bins=[x_edges, y_edges]
            )

            x_positions = xedges[:-1]
            y_positions = yedges[:-1]
            x_sizes = np.diff(xedges)
            y_sizes = np.diff(yedges)

            xpos, ypos = np.meshgrid(
                x_positions,
                y_positions,
                indexing="ij"
            )
            dx, dy = np.meshgrid(
                x_sizes,
                y_sizes,
                indexing="ij"
            )

            xpos = xpos.ravel()
            ypos = ypos.ravel()
            dx = dx.ravel()
            dy = dy.ravel()
            dz = hist.ravel()

            nonzero = dz > 0
            xpos = xpos[nonzero]
            ypos = ypos[nonzero]
            dx = dx[nonzero]
            dy = dy[nonzero]
            dz = dz[nonzero]

            if dz.size > 0:
                ax_3d.bar3d(
                    xpos,
                    ypos,
                    np.zeros_like(dz),
                    dx,
                    dy,
                    dz,
                    shade=True,
                    color=palette["bar3d_color"]
                )
                ax_3d.set_title("Joint WPM / error percentage distribution")
                ax_3d.set_xlabel("WPM")
                ax_3d.set_ylabel("Error percentage (%)")
                ax_3d.set_zlabel("Count")
            else:
                ax_3d.set_title("Joint WPM / error percentage distribution")
                ax_3d.text(
                    0.5,
                    0.5,
                    0.5,
                    "No combined WPM/error data available",
                    ha="center",
                    va="center",
                    color=palette["text_color"]
                )
                ax_3d.set_xticks([])
                ax_3d.set_yticks([])
                ax_3d.set_zticks([])
        else:
            ax_3d.set_title("Joint WPM / error percentage distribution")
            ax_3d.text(
                0.5,
                0.5,
                0.5,
                "No combined WPM/error data available",
                ha="center",
                va="center",
                color=palette["text_color"]
            )
            ax_3d.set_xticks([])
            ax_3d.set_yticks([])
            ax_3d.set_zticks([])

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_wpm,
                width=bar_width,
                color=palette["daily_speed_color"],
                label="Average WPM"
            )
            ax_time.bar(
                positions,
                daily_error,
                width=bar_width,
                color=palette["daily_error_color"],
                label="Average error %"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title("Daily averages (WPM vs error %)")
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title("Daily averages (WPM vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_letter_stats(self) -> None:
        """
        Visualize stored letter mode statistics (letters per minute and errors).
        """
        if self.is_sudden_death_active():
            self._show_sudden_death_stats(
                file_path=self.sudden_death_letter_stats_file_path,
                header=SUDDEN_DEATH_LETTER_STATS_FILE_HEADER,
                mode_label="letter",
                speed_label="Letters per minute",
                speed_short_label="Letters/min",
                correct_label="Correct letters"
            )
            return

        if not self.letter_stats_file_path.exists():
            messagebox.showinfo(
                "Letter statistics",
                "No letter statistics available yet. "
                "Finish at least one letter mode session."
            )
            return

        ensure_stats_file_header(
            self.letter_stats_file_path,
            LETTER_STATS_FILE_HEADER,
            create_if_missing=False
        )

        letters_per_minute: List[float] = []
        error_rates: List[float] = []
        daily_stats: dict = {}

        with self.letter_stats_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 3:
                    continue
                is_training_run = self._parse_training_flag(parts, 4)
                if not self._should_include_training_entry(is_training_run):
                    continue
                try:
                    day = datetime.strptime(
                        parts[0],
                        "%Y-%m-%d %H:%M:%S"
                    ).date()
                    lpm_val = float(parts[1])
                    err_val = float(parts[2])
                except ValueError:
                    continue
                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None
                letters_per_minute.append(lpm_val)
                error_rates.append(err_val)
                entry = daily_stats.setdefault(
                    day,
                    {
                        "speed_sum": 0.0,
                        "speed_count": 0,
                        "error_sum": 0.0,
                        "error_count": 0,
                        "duration_sum": 0.0,
                    }
                )
                entry["speed_sum"] += lpm_val
                entry["speed_count"] += 1
                entry["error_sum"] += err_val
                entry["error_count"] += 1
                if duration_val is not None:
                    entry["duration_sum"] += max(duration_val, 0.0)

        if not letters_per_minute:
            messagebox.showinfo(
                "Letter statistics",
                "No statistics available for the current filter selection."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_error: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_speed.append(stats["speed_sum"] / stats["speed_count"])
                    if stats["error_count"] > 0:
                        daily_error.append(
                            stats["error_sum"] / stats["error_count"]
                        )
                    else:
                        daily_error.append(0.0)
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_speed.append(0.0)
                    daily_error.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_3d = fig.add_subplot(grid_spec[1, :], projection="3d")
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_speed.hist(
            letters_per_minute,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_speed.set_title("Letters per minute distribution")
        ax_speed.set_xlabel("Letters per minute")
        ax_speed.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(
                error_rates,
                bins="auto",
                color=palette["hist_error_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_error.set_title("Error percentage distribution")
            ax_error.set_xlabel("Error percentage (%)")
            ax_error.set_ylabel("Frequency")
        else:
            ax_error.set_title("Error percentage distribution")
            ax_error.text(
                0.5,
                0.5,
                "No error data available",
                ha="center",
                va="center",
                transform=ax_error.transAxes,
                color=palette["text_color"]
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        if letters_per_minute and error_rates:
            lpm_arr = np.asarray(letters_per_minute, dtype=float)
            error_arr = np.asarray(error_rates, dtype=float)

            x_edges = np.histogram_bin_edges(lpm_arr, bins="auto")
            y_edges = np.histogram_bin_edges(error_arr, bins="auto")

            hist, xedges, yedges = np.histogram2d(
                lpm_arr,
                error_arr,
                bins=[x_edges, y_edges]
            )

            x_positions = xedges[:-1]
            y_positions = yedges[:-1]
            x_sizes = np.diff(xedges)
            y_sizes = np.diff(yedges)

            xpos, ypos = np.meshgrid(
                x_positions,
                y_positions,
                indexing="ij"
            )
            dx, dy = np.meshgrid(
                x_sizes,
                y_sizes,
                indexing="ij"
            )

            xpos = xpos.ravel()
            ypos = ypos.ravel()
            dx = dx.ravel()
            dy = dy.ravel()
            dz = hist.ravel()

            nonzero = dz > 0
            xpos = xpos[nonzero]
            ypos = ypos[nonzero]
            dx = dx[nonzero]
            dy = dy[nonzero]
            dz = dz[nonzero]

            if dz.size > 0:
                ax_3d.bar3d(
                    xpos,
                    ypos,
                    np.zeros_like(dz),
                    dx,
                    dy,
                    dz,
                    shade=True,
                    color=palette["bar3d_color"]
                )
                ax_3d.set_title("Joint letters/minute and error distribution")
                ax_3d.set_xlabel("Letters per minute")
                ax_3d.set_ylabel("Error percentage (%)")
                ax_3d.set_zlabel("Count")
            else:
                ax_3d.set_title("Joint letters/minute and error distribution")
                ax_3d.text(
                    0.5,
                    0.5,
                    0.5,
                    "No combined data available",
                    ha="center",
                    va="center",
                    color=palette["text_color"]
                )
                ax_3d.set_xticks([])
                ax_3d.set_yticks([])
                ax_3d.set_zticks([])
        else:
            ax_3d.set_title("Joint letters/minute and error distribution")
            ax_3d.text(
                0.5,
                0.5,
                0.5,
                "No combined data available",
                ha="center",
                va="center",
                color=palette["text_color"]
            )
            ax_3d.set_xticks([])
            ax_3d.set_yticks([])
            ax_3d.set_zticks([])

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_speed,
                width=bar_width,
                color=palette["daily_speed_color"],
                label="Average letters/min"
            )
            ax_time.bar(
                positions,
                daily_error,
                width=bar_width,
                color=palette["daily_error_color"],
                label="Average error %"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title("Daily averages (letters/min vs error %)")
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title("Daily averages (letters/min vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_special_stats(self) -> None:
        """
        Visualize stored special character mode statistics.
        """
        if self.is_sudden_death_active():
            self._show_sudden_death_stats(
                file_path=self.sudden_death_special_stats_file_path,
                header=SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER,
                mode_label="special",
                speed_label="Special chars per minute",
                speed_short_label="Special chars/min",
                correct_label="Correct symbols"
            )
            return

        if not self.special_stats_file_path.exists():
            messagebox.showinfo(
                "Special character statistics",
                "No special character statistics available yet. "
                "Finish at least one special mode session."
            )
            return

        ensure_stats_file_header(
            self.special_stats_file_path,
            SPECIAL_STATS_FILE_HEADER,
            create_if_missing=False
        )

        symbols_per_minute: List[float] = []
        error_rates: List[float] = []
        daily_stats: dict = {}

        with self.special_stats_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 3:
                    continue
                is_training_run = self._parse_training_flag(parts, 4)
                if not self._should_include_training_entry(is_training_run):
                    continue
                try:
                    day = datetime.strptime(
                        parts[0],
                        "%Y-%m-%d %H:%M:%S"
                    ).date()
                    spm_val = float(parts[1])
                    err_val = float(parts[2])
                except ValueError:
                    continue
                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None
                symbols_per_minute.append(spm_val)
                error_rates.append(err_val)
                entry = daily_stats.setdefault(
                    day,
                    {
                        "speed_sum": 0.0,
                        "speed_count": 0,
                        "error_sum": 0.0,
                        "error_count": 0,
                        "duration_sum": 0.0,
                    }
                )
                entry["speed_sum"] += spm_val
                entry["speed_count"] += 1
                entry["error_sum"] += err_val
                entry["error_count"] += 1
                if duration_val is not None:
                    entry["duration_sum"] += max(duration_val, 0.0)

        if not symbols_per_minute:
            messagebox.showinfo(
                "Special character statistics",
                "No statistics available for the current filter selection."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_error: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_speed.append(stats["speed_sum"] / stats["speed_count"])
                    if stats["error_count"] > 0:
                        daily_error.append(
                            stats["error_sum"] / stats["error_count"]
                        )
                    else:
                        daily_error.append(0.0)
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_speed.append(0.0)
                    daily_error.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_3d = fig.add_subplot(grid_spec[1, :], projection="3d")
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_speed.hist(
            symbols_per_minute,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_speed.set_title("Special chars per minute distribution")
        ax_speed.set_xlabel("Special chars per minute")
        ax_speed.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(
                error_rates,
                bins="auto",
                color=palette["hist_error_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_error.set_title("Error percentage distribution")
            ax_error.set_xlabel("Error percentage (%)")
            ax_error.set_ylabel("Frequency")
        else:
            ax_error.set_title("Error percentage distribution")
            ax_error.text(
                0.5,
                0.5,
                "No error data available",
                ha="center",
                va="center",
                transform=ax_error.transAxes,
                color=palette["text_color"]
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        if symbols_per_minute and error_rates:
            spm_arr = np.asarray(symbols_per_minute, dtype=float)
            error_arr = np.asarray(error_rates, dtype=float)

            x_edges = np.histogram_bin_edges(spm_arr, bins="auto")
            y_edges = np.histogram_bin_edges(error_arr, bins="auto")

            hist, xedges, yedges = np.histogram2d(
                spm_arr,
                error_arr,
                bins=[x_edges, y_edges]
            )

            x_positions = xedges[:-1]
            y_positions = yedges[:-1]
            x_sizes = np.diff(xedges)
            y_sizes = np.diff(yedges)

            xpos, ypos = np.meshgrid(
                x_positions,
                y_positions,
                indexing="ij"
            )
            dx, dy = np.meshgrid(
                x_sizes,
                y_sizes,
                indexing="ij"
            )

            xpos = xpos.ravel()
            ypos = ypos.ravel()
            dx = dx.ravel()
            dy = dy.ravel()
            dz = hist.ravel()

            nonzero = dz > 0
            xpos = xpos[nonzero]
            ypos = ypos[nonzero]
            dx = dx[nonzero]
            dy = dy[nonzero]
            dz = dz[nonzero]

            if dz.size > 0:
                ax_3d.bar3d(
                    xpos,
                    ypos,
                    np.zeros_like(dz),
                    dx,
                    dy,
                    dz,
                    shade=True,
                    color=palette["bar3d_color"]
                )
                ax_3d.set_title("Joint special chars/min and error distribution")
                ax_3d.set_xlabel("Special chars per minute")
                ax_3d.set_ylabel("Error percentage (%)")
                ax_3d.set_zlabel("Count")
            else:
                ax_3d.set_title("Joint special chars/min and error distribution")
                ax_3d.text(
                    0.5,
                    0.5,
                    0.5,
                    "No combined data available",
                    ha="center",
                    va="center",
                    color=palette["text_color"]
                )
                ax_3d.set_xticks([])
                ax_3d.set_yticks([])
                ax_3d.set_zticks([])
        else:
            ax_3d.set_title("Joint special chars/min and error distribution")
            ax_3d.text(
                0.5,
                0.5,
                0.5,
                "No combined data available",
                ha="center",
                va="center",
                color=palette["text_color"]
            )
            ax_3d.set_xticks([])
            ax_3d.set_yticks([])
            ax_3d.set_zticks([])

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_speed,
                width=bar_width,
                color=palette["daily_speed_color"],
                label="Average special chars/min"
            )
            ax_time.bar(
                positions,
                daily_error,
                width=bar_width,
                color=palette["daily_error_color"],
                label="Average error %"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title("Daily averages (special chars/min vs error %)")
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title("Daily averages (special chars/min vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_number_stats(self) -> None:
        """
        Visualize stored number mode statistics.
        """
        if self.is_sudden_death_active():
            self._show_sudden_death_stats(
                file_path=self.sudden_death_number_stats_file_path,
                header=SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER,
                mode_label="number",
                speed_label="Digits per minute",
                speed_short_label="Digits/min",
                correct_label="Correct digits"
            )
            return

        if not self.number_stats_file_path.exists():
            messagebox.showinfo(
                "Number statistics",
                "No number statistics available yet. "
                "Finish at least one number mode session."
            )
            return

        ensure_stats_file_header(
            self.number_stats_file_path,
            NUMBER_STATS_FILE_HEADER,
            create_if_missing=False
        )

        digits_per_minute: List[float] = []
        error_rates: List[float] = []
        daily_stats: dict = {}

        with self.number_stats_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 3:
                    continue
                is_training_run = self._parse_training_flag(parts, 4)
                if not self._should_include_training_entry(is_training_run):
                    continue
                try:
                    day = datetime.strptime(
                        parts[0],
                        "%Y-%m-%d %H:%M:%S"
                    ).date()
                    dpm_val = float(parts[1])
                    err_val = float(parts[2])
                except ValueError:
                    continue
                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None
                digits_per_minute.append(dpm_val)
                error_rates.append(err_val)
                entry = daily_stats.setdefault(
                    day,
                    {
                        "speed_sum": 0.0,
                        "speed_count": 0,
                        "error_sum": 0.0,
                        "error_count": 0,
                        "duration_sum": 0.0,
                    }
                )
                entry["speed_sum"] += dpm_val
                entry["speed_count"] += 1
                entry["error_sum"] += err_val
                entry["error_count"] += 1
                if duration_val is not None:
                    entry["duration_sum"] += max(duration_val, 0.0)

        if not digits_per_minute:
            messagebox.showinfo(
                "Number statistics",
                "No statistics available for the current filter selection."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_error: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_speed.append(stats["speed_sum"] / stats["speed_count"])
                    if stats["error_count"] > 0:
                        daily_error.append(
                            stats["error_sum"] / stats["error_count"]
                        )
                    else:
                        daily_error.append(0.0)
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_speed.append(0.0)
                    daily_error.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_3d = fig.add_subplot(grid_spec[1, :], projection="3d")
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_speed.hist(
            digits_per_minute,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_speed.set_title("Digits per minute distribution")
        ax_speed.set_xlabel("Digits per minute")
        ax_speed.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(
                error_rates,
                bins="auto",
                color=palette["hist_error_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_error.set_title("Error percentage distribution")
            ax_error.set_xlabel("Error percentage (%)")
            ax_error.set_ylabel("Frequency")
        else:
            ax_error.set_title("Error percentage distribution")
            ax_error.text(
                0.5,
                0.5,
                "No error data available",
                ha="center",
                va="center",
                transform=ax_error.transAxes,
                color=palette["text_color"]
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        if digits_per_minute and error_rates:
            dpm_arr = np.asarray(digits_per_minute, dtype=float)
            error_arr = np.asarray(error_rates, dtype=float)

            x_edges = np.histogram_bin_edges(dpm_arr, bins="auto")
            y_edges = np.histogram_bin_edges(error_arr, bins="auto")

            hist, xedges, yedges = np.histogram2d(
                dpm_arr,
                error_arr,
                bins=[x_edges, y_edges]
            )

            x_positions = xedges[:-1]
            y_positions = yedges[:-1]
            x_sizes = np.diff(xedges)
            y_sizes = np.diff(yedges)

            xpos, ypos = np.meshgrid(
                x_positions,
                y_positions,
                indexing="ij"
            )
            dx, dy = np.meshgrid(
                x_sizes,
                y_sizes,
                indexing="ij"
            )

            xpos = xpos.ravel()
            ypos = ypos.ravel()
            dx = dx.ravel()
            dy = dy.ravel()
            dz = hist.ravel()

            nonzero = dz > 0
            xpos = xpos[nonzero]
            ypos = ypos[nonzero]
            dx = dx[nonzero]
            dy = dy[nonzero]
            dz = dz[nonzero]

            if dz.size > 0:
                ax_3d.bar3d(
                    xpos,
                    ypos,
                    np.zeros_like(dz),
                    dx,
                    dy,
                    dz,
                    shade=True,
                    color=palette["bar3d_color"]
                )
                ax_3d.set_title("Joint digits/minute and error distribution")
                ax_3d.set_xlabel("Digits per minute")
                ax_3d.set_ylabel("Error percentage (%)")
                ax_3d.set_zlabel("Count")
            else:
                ax_3d.set_title("Joint digits/minute and error distribution")
                ax_3d.text(
                    0.5,
                    0.5,
                    0.5,
                    "No combined data available",
                    ha="center",
                    va="center",
                    color=palette["text_color"]
                )
                ax_3d.set_xticks([])
                ax_3d.set_yticks([])
                ax_3d.set_zticks([])
        else:
            ax_3d.set_title("Joint digits/minute and error distribution")
            ax_3d.text(
                0.5,
                0.5,
                0.5,
                "No combined data available",
                ha="center",
                va="center",
                color=palette["text_color"]
            )
            ax_3d.set_xticks([])
            ax_3d.set_yticks([])
            ax_3d.set_zticks([])

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_speed,
                width=bar_width,
                color=palette["daily_speed_color"],
                label="Average digits/min"
            )
            ax_time.bar(
                positions,
                daily_error,
                width=bar_width,
                color=palette["daily_error_color"],
                label="Average error %"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title("Daily averages (digits/min vs error %)")
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title("Daily averages (digits/min vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_general_stats(self) -> None:
        """
        Display cumulative time spent across all modes with heatmap and timeline views.
        """
        def _training_flag_index_from_header(header: str) -> int | None:
            columns = header.split(";")
            try:
                return columns.index(TRAINING_FLAG_COLUMN)
            except ValueError:
                return None

        stats_sources = [
            (
                self.stats_file_path,
                STATS_FILE_HEADER,
                "typing",
                _training_flag_index_from_header(STATS_FILE_HEADER)
            ),
            (
                self.letter_stats_file_path,
                LETTER_STATS_FILE_HEADER,
                "letter",
                _training_flag_index_from_header(LETTER_STATS_FILE_HEADER)
            ),
            (
                self.special_stats_file_path,
                SPECIAL_STATS_FILE_HEADER,
                "character",
                _training_flag_index_from_header(SPECIAL_STATS_FILE_HEADER)
            ),
            (
                self.number_stats_file_path,
                NUMBER_STATS_FILE_HEADER,
                "number",
                _training_flag_index_from_header(NUMBER_STATS_FILE_HEADER)
            ),
            (
                self.sudden_death_typing_stats_file_path,
                SUDDEN_DEATH_TYPING_STATS_FILE_HEADER,
                "typing",
                _training_flag_index_from_header(
                    SUDDEN_DEATH_TYPING_STATS_FILE_HEADER
                )
            ),
            (
                self.sudden_death_letter_stats_file_path,
                SUDDEN_DEATH_LETTER_STATS_FILE_HEADER,
                "letter",
                _training_flag_index_from_header(
                    SUDDEN_DEATH_LETTER_STATS_FILE_HEADER
                )
            ),
            (
                self.sudden_death_special_stats_file_path,
                SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER,
                "character",
                _training_flag_index_from_header(
                    SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER
                )
            ),
            (
                self.sudden_death_number_stats_file_path,
                SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER,
                "number",
                _training_flag_index_from_header(
                    SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER
                )
            )
        ]

        mode_labels: dict[str, str] = {
            "typing": "Typing text",
            "letter": "Letter mode",
            "number": "Number mode",
            "character": "Character mode"
        }

        daily_seconds: dict[date, float] = {}
        total_seconds = 0.0
        mode_seconds: dict[str, float] = {key: 0.0 for key in mode_labels}
        training_seconds = {"training": 0.0, "regular": 0.0}

        def _is_training_run(parts: list[str], flag_index: int | None) -> bool:
            if flag_index is None or flag_index >= len(parts):
                return False
            return parts[flag_index].strip().lower() in {"1", "true", "yes", "y"}

        for path, header, mode_key, training_index in stats_sources:
            if not path.exists():
                continue
            ensure_stats_file_header(
                path,
                header,
                create_if_missing=False
            )
            with path.open("r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line or line == header:
                        continue
                    parts = line.split(";")
                    if len(parts) <= 3:
                        continue
                    try:
                        timestamp = datetime.strptime(
                            parts[0],
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        continue
                    try:
                        duration_seconds = float(parts[3])
                    except ValueError:
                        continue
                    duration_seconds = max(duration_seconds, 0.0)
                    if duration_seconds == 0.0:
                        continue
                    day = timestamp.date()
                    daily_seconds[day] = (
                        daily_seconds.get(day, 0.0) + duration_seconds
                    )
                    total_seconds += duration_seconds
                    mode_seconds[mode_key] += duration_seconds
                    if _is_training_run(parts, training_index):
                        training_seconds["training"] += duration_seconds
                    else:
                        training_seconds["regular"] += duration_seconds

        today = datetime.now().date()
        start_date = today - timedelta(days=364)
        start_week = start_date - timedelta(days=start_date.weekday())
        end_week = today + timedelta(days=(6 - today.weekday()))
        total_days = (end_week - start_week).days + 1
        num_weeks = max(total_days // 7, 1)

        heatmap_data = np.full((7, num_weeks), np.nan, dtype=float)
        date_grid: list[list[date | None]] = [
            [None for _ in range(num_weeks)] for _ in range(7)
        ]

        current_day = start_week
        for idx in range(total_days):
            week_idx = idx // 7
            weekday_idx = current_day.weekday()
            if week_idx >= num_weeks:
                break
            date_grid[weekday_idx][week_idx] = current_day
            if start_date <= current_day <= today:
                seconds = daily_seconds.get(current_day, 0.0)
                heatmap_data[weekday_idx, week_idx] = seconds / 60.0
            current_day += timedelta(days=1)

        monthly_totals: dict[tuple[int, int], float] = {}
        for day_value, seconds in daily_seconds.items():
            if start_date <= day_value <= today:
                key = (day_value.year, day_value.month)
                monthly_totals[key] = (
                    monthly_totals.get(key, 0.0) + seconds / 60.0
                )

        def _first_of_month(value: date) -> date:
            return date(value.year, value.month, 1)

        monthly_labels: list[str] = []
        monthly_minutes: list[float] = []
        cumulative_minutes: list[float] = []
        cumulative_total = 0.0
        current_month = _first_of_month(start_date)
        last_month = _first_of_month(today)
        while current_month <= last_month:
            key = (current_month.year, current_month.month)
            minutes_value = monthly_totals.get(key, 0.0)
            cumulative_total += minutes_value
            monthly_labels.append(current_month.strftime("%b %Y"))
            monthly_minutes.append(minutes_value)
            cumulative_minutes.append(cumulative_total)
            if current_month.month == 12:
                current_month = date(current_month.year + 1, 1, 1)
            else:
                current_month = date(
                    current_month.year,
                    current_month.month + 1,
                    1
                )

        max_minutes = np.nanmax(heatmap_data)
        if not np.isfinite(max_minutes) or max_minutes == 0.0:
            max_minutes = 1.0

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(14, 10.2))
        gridspec = fig.add_gridspec(
            3,
            2,
            height_ratios=(2.3, 1.15, 0.9),
            hspace=0.65,
            wspace=0.12
        )
        ax_heatmap = fig.add_subplot(gridspec[0, :])
        ax_time_spent = fig.add_subplot(gridspec[1, :])
        ax_modes = fig.add_subplot(gridspec[2, 0])
        ax_training = fig.add_subplot(gridspec[2, 1])
        self._configure_figure_window(fig)
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "time_heatmap",
            [
                palette["heatmap_low_color"],
                palette["heatmap_high_color"]
            ]
        )
        cmap.set_bad(color=palette["heatmap_bad_color"])
        norm = mcolors.Normalize(vmin=0.0, vmax=max_minutes)
        im = ax_heatmap.imshow(
            heatmap_data,
            aspect="auto",
            origin="upper",
            cmap=cmap,
            norm=norm
        )

        colorbar = fig.colorbar(im, ax=ax_heatmap, pad=0.02)
        colorbar.set_label("Minutes spent per day")

        weekday_labels = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]
        ax_heatmap.set_yticks(range(7))
        ax_heatmap.set_yticklabels(weekday_labels)

        week_start_days = [
            start_week + timedelta(days=week_idx * 7)
            for week_idx in range(num_weeks)
        ]
        tick_positions: List[int] = []
        tick_labels: List[str] = []
        for idx, week_start in enumerate(week_start_days):
            if idx == 0 or week_start.day <= 7:
                tick_positions.append(idx)
                tick_labels.append(week_start.strftime("%b %d"))

        if tick_positions:
            ax_heatmap.set_xticks(tick_positions)
            ax_heatmap.set_xticklabels(tick_labels, rotation=45, ha="right")

        ax_heatmap.set_xlabel("Weeks (starting Mondays)")
        ax_heatmap.set_ylabel("Day of week")
        ax_heatmap.set_title("Daily time spent (last 365 days)")

        month_positions = np.arange(len(monthly_minutes))
        ax_time_spent.bar(
            month_positions,
            monthly_minutes,
            width=0.5,
            color=palette["time_per_day_bar_color"],
            label="Time per month (min)"
        )
        ax_cumulative = ax_time_spent.twinx()
        cumulative_line, = ax_cumulative.plot(
            month_positions,
            cumulative_minutes,
            color=palette["time_cumulative_line_color"],
            marker="o",
            markerfacecolor=palette["axes_facecolor"],
            markeredgecolor=palette["time_cumulative_line_color"],
            linewidth=1.8,
            label="Cumulative time (min)"
        )
        ax_time_spent.set_xticks(month_positions)
        ax_time_spent.set_xticklabels(
            monthly_labels,
            rotation=45,
            ha="right"
        )
        ax_time_spent.set_ylabel("Minutes per month")
        ax_cumulative.set_ylabel("Cumulative minutes")
        ax_time_spent.set_xlabel("Month")
        ax_time_spent.set_title("Time spent progression (last 365 days)")
        formatter = mticker.FormatStrFormatter("%.0f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_cumulative.yaxis.set_major_formatter(formatter)
        handles, labels = ax_time_spent.get_legend_handles_labels()
        handles2, labels2 = ax_cumulative.get_legend_handles_labels()
        legend = ax_time_spent.legend(
            handles + handles2,
            labels + labels2,
            loc="upper left",
            frameon=False
        )
        self._style_legend(legend, palette)

        annotation = ax_heatmap.annotate(
            "",
            xy=(0, 0),
            xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(
                boxstyle="round",
                fc=palette["annotation_face_color"],
                ec=palette["annotation_edge_color"],
                alpha=0.9
            ),
            arrowprops=dict(
                arrowstyle="->",
                color=palette["annotation_edge_color"]
            ),
            color=palette["annotation_text_color"]
        )
        annotation.set_visible(False)

        def _format_minutes(value: float) -> str:
            if value >= 60.0:
                return f"{value / 60.0:.1f} h"
            return f"{value:.1f} min"

        def _on_mouse_move(event) -> None:
            if (
                event.inaxes != ax_heatmap
                or event.xdata is None
                or event.ydata is None
            ):
                if annotation.get_visible():
                    annotation.set_visible(False)
                    fig.canvas.draw_idle()
                return
            week_idx = int(event.xdata)
            weekday_idx = int(event.ydata)
            if (
                week_idx < 0
                or week_idx >= num_weeks
                or weekday_idx < 0
                or weekday_idx >= 7
            ):
                if annotation.get_visible():
                    annotation.set_visible(False)
                    fig.canvas.draw_idle()
                return
            date_value = date_grid[weekday_idx][week_idx]
            cell_value = heatmap_data[weekday_idx, week_idx]
            if date_value is None or not np.isfinite(cell_value):
                if annotation.get_visible():
                    annotation.set_visible(False)
                    fig.canvas.draw_idle()
                return
            annotation.xy = (week_idx, weekday_idx)
            if week_idx >= num_weeks - 5:
                annotation.xytext = (-15, 15)
                annotation.set_ha("right")
            else:
                annotation.xytext = (15, 15)
                annotation.set_ha("left")
            annotation.set_text(
                f"{date_value.strftime('%Y-%m-%d (%a)')}\n"
                f"Time: {_format_minutes(cell_value)}"
            )
            annotation.set_visible(True)
            fig.canvas.draw_idle()

        def _build_pie_chart(
            ax: plt.Axes,
            values: list[float],
            label_texts: list[str],
            colors: list[str],
            title: str
        ) -> None:
            ax.clear()
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            total = sum(values)
            if total <= 0.0:
                ax.text(
                    0.5,
                    0.5,
                    "No time recorded yet",
                    ha="center",
                    va="center",
                    color=palette["text_color"]
                )
                ax.set_title(title, pad=12)
                return
            wedges, _ = ax.pie(
                values,
                colors=colors,
                startangle=90
            )
            legend_entries = []
            for label, value in zip(label_texts, values):
                percent = (value / total * 100.0) if total else 0.0
                legend_entries.append(
                    f"{label}: {percent:.1f}% ({_format_minutes(value)})"
                )
            legend = ax.legend(
                wedges,
                legend_entries,
                loc="center left",
                bbox_to_anchor=(0.9, 0.5),
                frameon=False
            )
            self._style_legend(legend, palette)
            ax.set_title(title, pad=16)

        fig.canvas.mpl_connect("motion_notify_event", _on_mouse_move)

        mode_order = ["typing", "letter", "number", "character"]
        mode_minutes = [mode_seconds[key] / 60.0 for key in mode_order]
        training_minutes = [
            training_seconds["training"] / 60.0,
            training_seconds["regular"] / 60.0
        ]

        mode_colors = palette["pie_mode_colors"]
        _build_pie_chart(
            ax_modes,
            mode_minutes,
            [mode_labels[key] for key in mode_order],
            mode_colors,
            "Time spent by mode"
        )

        training_labels = ["Training mode", "Non-training mode"]
        training_colors = palette["pie_training_colors"]
        _build_pie_chart(
            ax_training,
            training_minutes,
            training_labels,
            training_colors,
            "Training vs non-training time"
        )

        self._apply_plot_theme(fig, palette)
        fig.tight_layout()
        fig.subplots_adjust(top=0.94, bottom=0.02, left=0.05, right=0.98)
        plt.show()


def main() -> None:
    """
    Entry point for the typing trainer application.
    """
    text_file_path = get__file_path(TEXT_FILE_NAME)
    texts = load_or_create_texts(text_file_path)

    root = tk.Tk()
    TypingTrainerApp(root, texts)
    root.mainloop()


if __name__ == "__main__":
    main()
