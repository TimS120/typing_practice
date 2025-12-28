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
from typing import Any, List
import ctypes
from ctypes import wintypes
import sys


import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

try:
    import winreg
except ImportError:
    winreg = None

from .backend import (
    calculate_end_error_percentage,
    save_blind_letter_result,
    save_blind_number_result,
    save_blind_special_result,
    save_blind_typing_result,
    save_letter_result,
    save_number_result,
    save_special_result,
    save_sudden_death_letter_result,
    save_sudden_death_number_result,
    save_sudden_death_special_result,
    save_sudden_death_wpm_result,
    save_wpm_result,
)
from .plot_utils import PlotMixin
from .io_utils import (
    BLIND_LETTER_STATS_FILE_HEADER,
    BLIND_LETTER_STATS_FILE_NAME,
    BLIND_NUMBER_STATS_FILE_HEADER,
    BLIND_NUMBER_STATS_FILE_NAME,
    BLIND_SPECIAL_STATS_FILE_HEADER,
    BLIND_SPECIAL_STATS_FILE_NAME,
    BLIND_TYPING_STATS_FILE_HEADER,
    BLIND_TYPING_STATS_FILE_NAME,
    LETTER_STATS_FILE_HEADER,
    LETTER_STATS_FILE_NAME,
    NUMBER_STATS_FILE_HEADER,
    NUMBER_STATS_FILE_NAME,
    SPECIAL_STATS_FILE_HEADER,
    SPECIAL_STATS_FILE_NAME,
    STATS_FILE_HEADER,
    STATS_FILE_NAME,
    SUDDEN_DEATH_LETTER_STATS_FILE_HEADER,
    SUDDEN_DEATH_LETTER_STATS_FILE_NAME,
    SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER,
    SUDDEN_DEATH_NUMBER_STATS_FILE_NAME,
    SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER,
    SUDDEN_DEATH_SPECIAL_STATS_FILE_NAME,
    SUDDEN_DEATH_TYPING_STATS_FILE_HEADER,
    SUDDEN_DEATH_TYPING_STATS_FILE_NAME,
    TRAINING_FLAG_COLUMN,
    ensure_stats_file_header,
    get__file_path,
)

GA_ROOT = 2
WCA_USEDARKMODECOLORS = 26


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t)
    ]

GUI_WINDOW_XY = "1350x550"
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
SUDDEN_DEATH_MODE_OPTIONS = [
    ("standard", "Standard"),
    ("sudden", "Sudden death"),
    ("blind", "Blind mode"),
]
DEFAULT_SUDDEN_DEATH_MODE_KEY = "standard"
SUDDEN_DEATH_MODE_LABEL_BY_KEY = {
    key: label for key, label in SUDDEN_DEATH_MODE_OPTIONS
}
SUDDEN_DEATH_MODE_KEY_BY_LABEL = {
    label: key for key, label in SUDDEN_DEATH_MODE_OPTIONS
}
BLIND_CURSOR_TAG = "blind_cursor"
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
    "titlebar_border": "#c0c0c0",
    "blind_highlight": "#d0d0d0",
    "blind_mask_foreground": "#ffffff",
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
    "titlebar_border": "#333333",
    "blind_highlight": "#555555",
    "blind_mask_foreground": "#1f1f1f",
}




class TypingTrainerApp(PlotMixin):
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
        self.blind_typing_stats_file_path: Path = get__file_path(
            BLIND_TYPING_STATS_FILE_NAME
        )
        self.blind_letter_stats_file_path: Path = get__file_path(
            BLIND_LETTER_STATS_FILE_NAME
        )
        self.blind_special_stats_file_path: Path = get__file_path(
            BLIND_SPECIAL_STATS_FILE_NAME
        )
        self.blind_number_stats_file_path: Path = get__file_path(
            BLIND_NUMBER_STATS_FILE_NAME
        )

        self.current_font_size: int = DEFAULT_FONT_SIZE
        self.text_font: tkfont.Font | None = None
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
        self.letter_input_history: List[str] = []
        self.special_input_history: List[str] = []
        self.number_input_history: List[str] = []
        self.last_session_mode: str = "typing"
        self.style = ttk.Style()
        self.dark_mode_enabled: bool = self._detect_system_dark_mode()
        self.dark_mode_var = tk.BooleanVar(
            master=self.master,
            value=self.dark_mode_enabled
        )
        self.sudden_death_enabled: bool = False
        default_sd_mode_label = SUDDEN_DEATH_MODE_LABEL_BY_KEY[
            DEFAULT_SUDDEN_DEATH_MODE_KEY
        ]
        self.sudden_death_mode_var = tk.StringVar(
            master=self.master,
            value=default_sd_mode_label
        )
        self.active_mode_key = DEFAULT_SUDDEN_DEATH_MODE_KEY
        self.training_run_var = tk.BooleanVar(master=self.master, value=False)
        default_filter_label = STATS_FILTER_LABEL_BY_KEY[DEFAULT_STATS_FILTER_KEY]
        self.stats_filter_var = tk.StringVar(
            master=self.master,
            value=default_filter_label
        )
        self.sudden_death_failure_triggered: bool = False
        self.blind_reveal_active: bool = False
        self._title_bar_refresh_job: str | None = None
        self.sudden_death_mode_combobox: ttk.Combobox | None = None

        self._build_gui()


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
            command=self.on_load_random
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
        top_right_frame.columnconfigure(6, weight=0)

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
        sudden_death_mode_values = [
            label for _, label in SUDDEN_DEATH_MODE_OPTIONS
        ]
        sd_mode_label = ttk.Label(top_right_frame, text="Mode:")
        sd_mode_label.grid(row=0, column=5, padx=(10, 0), sticky="e")
        self.sudden_death_mode_combobox = ttk.Combobox(
            top_right_frame,
            textvariable=self.sudden_death_mode_var,
            values=sudden_death_mode_values,
            state="readonly",
            width=12
        )
        self.sudden_death_mode_combobox.grid(row=0, column=6, padx=(5, 0), sticky="e")
        self.sudden_death_mode_combobox.bind(
            "<<ComboboxSelected>>",
            self.on_sudden_death_mode_change
        )

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
        return self.sudden_death_enabled

    def _get_sudden_death_mode_key(self) -> str:
        """
        Return the internal key of the currently selected sudden death sub-mode.
        """
        label = self.sudden_death_mode_var.get()
        return SUDDEN_DEATH_MODE_KEY_BY_LABEL.get(
            label,
            DEFAULT_SUDDEN_DEATH_MODE_KEY
        )

    def is_blind_mode_active(self) -> bool:
        """
        Return True when sudden death is enabled and blind mode is selected.
        """
        return self._get_sudden_death_mode_key() == "blind"

    def on_sudden_death_mode_change(self, event: tk.Event | None = None) -> None:
        """
        Update UI aspects when the sudden death sub-mode changes.
        """
        previous_mode = self.active_mode_key
        mode_key = self._get_sudden_death_mode_key()
        should_enable_sudden = mode_key == "sudden"
        if should_enable_sudden != self.sudden_death_enabled:
            self._apply_sudden_death_state(should_enable_sudden)
        elif mode_key != previous_mode:
            self.reset_session(clear_display=False)
        self.active_mode_key = mode_key
        if mode_key == "blind":
            self.info_label.configure(
                text="Blind mode enabled. Load a text or start a mode."
            )
        elif mode_key == "standard" and not self.is_sudden_death_active():
            self.info_label.configure(
                text="Standard mode active. Load a text or start a mode."
            )
        self._update_input_visibility()
        self._update_blind_target_indicator()

    def _apply_sudden_death_state(self, enabled: bool) -> None:
        """
        Apply visual and state changes when sudden death mode toggles.
        """
        if self.sudden_death_enabled == enabled:
            return
        self.sudden_death_enabled = enabled
        self.reset_session(clear_display=False)
        self._update_input_visibility()
        self._update_blind_target_indicator()
        if enabled:
            self.info_label.configure(
                text="Sudden death enabled. Load a text or start a mode."
            )
        else:
            self.info_label.configure(
                text="Sudden death disabled. Normal sessions restored."
            )

    def _update_input_visibility(self) -> None:
        """
        Hide or show the input text contents depending on blind mode.
        """
        theme = DARK_THEME if self.dark_mode_enabled else LIGHT_THEME
        if self.is_blind_mode_active():
            if self.blind_reveal_active:
                self.input_text.configure(foreground=theme["input_foreground"])
            else:
                mask_color = theme.get(
                    "blind_mask_foreground",
                    theme["input_background"]
                )
                self.input_text.configure(foreground=mask_color)
        else:
            self.input_text.configure(foreground=theme["input_foreground"])

    def _update_blind_target_indicator(self, typed_length: int | None = None) -> None:
        """
        Highlight the current target character while typing blindly.
        """
        self.display_text.configure(state="normal")
        self.display_text.tag_remove(BLIND_CURSOR_TAG, "1.0", tk.END)
        if (
            not self.is_blind_mode_active()
            or self.is_letter_mode
            or self.is_special_mode
            or self.is_number_mode
            or not self.target_text
        ):
            self.display_text.configure(state="disabled")
            return
        if typed_length is None:
            typed_length = len(self.input_text.get("1.0", "end-1c"))
        if typed_length >= len(self.target_text):
            self.display_text.configure(state="disabled")
            return
        start = f"1.0 + {typed_length} chars"
        end = f"1.0 + {typed_length + 1} chars"
        self.display_text.tag_add(BLIND_CURSOR_TAG, start, end)
        self.display_text.configure(state="disabled")

    def _show_blind_final_text(self, typed_text: str) -> None:
        """
        Reveal the typed text inside the input box with error highlighting.
        """
        if not self.is_blind_mode_active():
            return

        self.blind_reveal_active = True
        self._update_input_visibility()

        self._render_typed_text_with_errors(typed_text, self.target_text)

    def _render_typed_text_with_errors(
        self,
        typed_text: str,
        target_text: str
    ) -> None:
        """
        Populate the input widget with typed text and highlight mismatches.
        """
        self.input_text.delete("1.0", tk.END)
        self.input_text.tag_remove("error", "1.0", tk.END)

        if not typed_text:
            return

        self.input_text.insert("1.0", typed_text)

        for index, char in enumerate(typed_text):
            target_char = target_text[index] if index < len(target_text) else ""
            if char != target_char:
                start = f"1.0 + {index} chars"
                end = f"1.0 + {index + 1} chars"
                self.input_text.tag_add("error", start, end)

        self.input_text.see("end")

    def _display_sequence_result(
        self,
        typed_text: str,
        target_sequence: str
    ) -> None:
        """
        Show the typed characters for single-character modes with errors marked.
        """
        if self.is_blind_mode_active() and not self.blind_reveal_active:
            self.blind_reveal_active = True
            self._update_input_visibility()

        self._render_typed_text_with_errors(typed_text, target_sequence)

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
        self.display_text.tag_configure(
            BLIND_CURSOR_TAG,
            background=theme["blind_highlight"],
            foreground=theme["text"]
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
        self._update_input_visibility()
        self._update_blind_target_indicator()

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
        Select a random text from the provided list and load it.
        """
        if not self.texts:
            messagebox.showinfo(
                "Selection",
                "No texts are available to load."
            )
            return

        index = random.randrange(len(self.texts))
        self.text_listbox.selection_clear(0, tk.END)
        self.text_listbox.selection_set(index)
        self._load_text_from_index(index)


    def _load_text_from_index(self, index: int) -> None:
        """
        Resolve the listbox index to a text string and display it.
        """
        total_entries = len(self.texts)
        if index < 0 or index >= total_entries:
            messagebox.showinfo(
                "Selection",
                "The selected text could not be loaded."
            )
            return

        self.selected_text = self.texts[index]

        self._apply_loaded_text()


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
        self._update_blind_target_indicator(0)

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

        self.letter_input_history = []
        self.special_input_history = []
        self.number_input_history = []
        self.blind_reveal_active = False

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
        self._update_input_visibility()
        self._update_blind_target_indicator()


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

        if (not self.is_sudden_death_active()) and event.keysym == "BackSpace":
            if self._handle_letter_backspace():
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

        is_correct = current_char == target_letter
        advance_on_error = self.is_blind_mode_active()

        if is_correct:
            self.letter_input_history.append(current_char)
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

        # incorrect input
        self.letter_errors += 1

        if self.is_sudden_death_active():
            self.finish_letter_mode_session(sudden_death=True)
            return

        if advance_on_error:
            self.letter_input_history.append(current_char)
            self.letter_index += 1
            self.input_text.delete("1.0", tk.END)
            if self.letter_index >= self.letter_total_letters:
                self.finish_letter_mode_session()
            else:
                self._update_letter_display()
                self.update_letter_status_label()
            return

        self.input_text.delete("1.0", tk.END)
        self.update_letter_status_label()

    def _handle_letter_backspace(self) -> bool:
        """
        Allow undoing the last confirmed letter when not in sudden death mode.
        """
        if self.letter_index <= 0 or not self.letter_input_history:
            return False

        self.letter_index -= 1
        last_char = self.letter_input_history.pop()
        target_letter = (
            self.letter_sequence[self.letter_index]
            if self.letter_index < len(self.letter_sequence)
            else ""
        )
        if last_char == target_letter:
            if self.letter_correct_letters > 0:
                self.letter_correct_letters -= 1
        else:
            if self.letter_errors > 0:
                self.letter_errors -= 1

        self.input_text.delete("1.0", tk.END)
        self._update_letter_display()
        self.update_letter_status_label()
        return True


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
            progress = f"{self.letter_index}/{self.letter_total_letters}"

        if self.is_blind_mode_active():
            error_text = "Errors: hidden"
        else:
            error_text = f"Errors: {self.letter_errors}"

        self.wpm_label.configure(
            text=(
                f"Letter mode  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Letters/min: {letters_per_minute:.1f}  |  "
                f"Progress: {progress}  |  "
                f"{error_text}"
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
        typed_letters_text = "".join(self.letter_input_history)
        typed_letters_count = len(typed_letters_text)
        blind_end_error_percentage: float | None = None
        if self.is_blind_mode_active() and typed_letters_count > 0:
            if sudden_death:
                total_targets = max(typed_letters_count, 1)
            else:
                total_targets = max(self.letter_total_letters, 1)
            target_letters = "".join(self.letter_sequence[:total_targets])
            blind_end_error_percentage = calculate_end_error_percentage(
                target_letters,
                typed_letters_text,
                total_targets
            )

        if sudden_death:
            correct_letters = self.letter_correct_letters
            if not self.is_blind_mode_active():
                save_sudden_death_letter_result(
                    self.sudden_death_letter_stats_file_path,
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
                    + (
                        f"  |  End error %: {blind_end_error_percentage:.1f}"
                        if blind_end_error_percentage is not None
                        else ""
                    )
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
                    + (
                        f"  |  End error %: {blind_end_error_percentage:.1f}"
                        if blind_end_error_percentage is not None
                        else ""
                    )
                )
        else:
            total_letters = max(self.letter_total_letters, 1)
            error_percentage = (self.letter_errors / total_letters) * 100.0
            if not self.is_blind_mode_active():
                save_letter_result(
                    self.letter_stats_file_path,
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
            if self.is_blind_mode_active():
                if blind_end_error_percentage is not None:
                    error_summary = (
                        f"End error %: {blind_end_error_percentage:.1f}"
                    )
                else:
                    error_summary = "Errors: hidden"
            else:
                error_summary = (
                    f"Errors: {self.letter_errors}  |  "
                    f"Error %: {error_percentage:.1f}"
                )
            summary = (
                f"Letter mode complete  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Letters/min: {letters_per_minute:.1f}  |  "
                f"{error_summary}"
            )

        target_letters_for_display = "".join(
            self.letter_sequence[:len(typed_letters_text)]
        )

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        display_content = (
            f"{display_message}\n\nTarget sequence:\n{target_letters_for_display}"
        )
        self.display_text.insert("1.0", display_content)
        self.display_text.configure(state="disabled")

        self.info_label.configure(text=info_message)
        self.wpm_label.configure(text=summary)

        self._display_sequence_result(
            typed_letters_text,
            target_letters_for_display
        )

        self.is_letter_mode = False
        self.start_time = None
        self.letter_sequence = []
        self.letter_index = 0
        self.letter_total_letters = 0
        self.letter_errors = 0
        self.letter_correct_letters = 0
        self.letter_input_history = []
        self.last_session_mode = "letter"

        if blind_end_error_percentage is not None:
            save_blind_letter_result(
                self.blind_letter_stats_file_path,
                letters_per_minute=letters_per_minute,
                typed_letters=typed_letters_count,
                duration_seconds=elapsed_seconds,
                completed=completed_sequence if sudden_death else True,
                end_error_percentage=blind_end_error_percentage,
                is_training_run=self.training_run_var.get()
            )


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

        if (not self.is_sudden_death_active()) and event.keysym == "BackSpace":
            if self._handle_special_backspace():
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

        is_correct = current_char == target_symbol
        advance_on_error = self.is_blind_mode_active()

        if is_correct:
            self.special_input_history.append(current_char)
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

        # incorrect input
        self.special_errors += 1

        if self.is_sudden_death_active():
            self.finish_special_mode_session(sudden_death=True)
            return

        if advance_on_error:
            self.special_input_history.append(current_char)
            self.special_index += 1
            self.input_text.delete("1.0", tk.END)
            if self.special_index >= self.special_total_chars:
                self.finish_special_mode_session()
            else:
                self._update_special_display()
                self.update_special_status_label()
            return

        self.input_text.delete("1.0", tk.END)
        self.update_special_status_label()

    def _handle_special_backspace(self) -> bool:
        """
        Allow undoing the last confirmed symbol when not in sudden death mode.
        """
        if self.special_index <= 0 or not self.special_input_history:
            return False

        self.special_index -= 1
        last_char = self.special_input_history.pop()
        target_symbol = (
            self.special_sequence[self.special_index]
            if self.special_index < len(self.special_sequence)
            else ""
        )
        if last_char == target_symbol:
            if self.special_correct_chars > 0:
                self.special_correct_chars -= 1
        else:
            if self.special_errors > 0:
                self.special_errors -= 1
        self.input_text.delete("1.0", tk.END)
        self._update_special_display()
        self.update_special_status_label()
        return True

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
            progress = f"{self.special_index}/{self.special_total_chars}"

        if self.is_blind_mode_active():
            error_text = "Errors: hidden"
        else:
            error_text = f"Errors: {self.special_errors}"

        self.wpm_label.configure(
            text=(
                f"Special char mode  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Symbols/min: {symbols_per_minute:.1f}  |  "
                f"Progress: {progress}  |  "
                f"{error_text}"
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
        typed_symbols_text = "".join(self.special_input_history)
        typed_symbols_count = len(typed_symbols_text)
        blind_end_error_percentage: float | None = None
        if self.is_blind_mode_active() and typed_symbols_count > 0:
            if sudden_death:
                total_targets = max(typed_symbols_count, 1)
            else:
                total_targets = max(self.special_total_chars, 1)
            target_symbols = "".join(self.special_sequence[:total_targets])
            blind_end_error_percentage = calculate_end_error_percentage(
                target_symbols,
                typed_symbols_text,
                total_targets
            )

        if sudden_death:
            correct_symbols = self.special_correct_chars
            if not self.is_blind_mode_active():
                save_sudden_death_special_result(
                    self.sudden_death_special_stats_file_path,
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
                    + (
                        f"  |  End error %: {blind_end_error_percentage:.1f}"
                        if blind_end_error_percentage is not None
                        else ""
                    )
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
                    + (
                        f"  |  End error %: {blind_end_error_percentage:.1f}"
                        if blind_end_error_percentage is not None
                        else ""
                    )
                )
        else:
            total_symbols = max(self.special_total_chars, 1)
            error_percentage = (self.special_errors / total_symbols) * 100.0
            if not self.is_blind_mode_active():
                save_special_result(
                    self.special_stats_file_path,
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
            if self.is_blind_mode_active():
                if blind_end_error_percentage is not None:
                    error_summary = (
                        f"End error %: {blind_end_error_percentage:.1f}"
                    )
                else:
                    error_summary = "Errors: hidden"
            else:
                error_summary = (
                    f"Errors: {self.special_errors}  |  "
                    f"Error %: {error_percentage:.1f}"
                )
            summary = (
                f"Special mode complete  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Symbols/min: {symbols_per_minute:.1f}  |  "
                f"{error_summary}"
            )

        target_symbols_for_display = "".join(
            self.special_sequence[:len(typed_symbols_text)]
        )

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        display_content = (
            f"{display_message}\n\nTarget sequence:\n{target_symbols_for_display}"
        )
        self.display_text.insert("1.0", display_content)
        self.display_text.configure(state="disabled")

        self.info_label.configure(text=info_message)
        self.wpm_label.configure(text=summary)

        self._display_sequence_result(
            typed_symbols_text,
            target_symbols_for_display
        )

        self.is_special_mode = False
        self.start_time = None
        self.special_sequence = []
        self.special_index = 0
        self.special_total_chars = 0
        self.special_errors = 0
        self.special_correct_chars = 0
        self.special_input_history = []
        self.last_session_mode = "special"

        if blind_end_error_percentage is not None:
            save_blind_special_result(
                self.blind_special_stats_file_path,
                symbols_per_minute=symbols_per_minute,
                typed_symbols=typed_symbols_count,
                duration_seconds=elapsed_seconds,
                completed=completed_sequence if sudden_death else True,
                end_error_percentage=blind_end_error_percentage,
                is_training_run=self.training_run_var.get()
            )


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

        if (not self.is_sudden_death_active()) and event.keysym == "BackSpace":
            if self._handle_number_backspace():
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

        is_correct = current_char == target_digit
        advance_on_error = self.is_blind_mode_active()

        if is_correct:
            self.number_input_history.append(current_char)
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

        # incorrect input
        self.number_errors += 1

        if self.is_sudden_death_active():
            self.finish_number_mode_session(sudden_death=True)
            return

        if advance_on_error:
            self.number_input_history.append(current_char)
            self.number_index += 1
            self.input_text.delete("1.0", tk.END)
            if self.number_index >= self.number_total_digits:
                self.finish_number_mode_session()
            else:
                self._update_number_display()
                self.update_number_status_label()
            return

        self.input_text.delete("1.0", tk.END)
        self.update_number_status_label()

    def _handle_number_backspace(self) -> bool:
        """
        Allow undoing the last confirmed digit when not in sudden death mode.
        """
        if self.number_index <= 0 or not self.number_input_history:
            return False

        self.number_index -= 1
        last_char = self.number_input_history.pop()
        target_digit = (
            self.number_sequence[self.number_index]
            if self.number_index < len(self.number_sequence)
            else ""
        )
        if last_char == target_digit:
            if self.number_correct_digits > 0:
                self.number_correct_digits -= 1
        else:
            if self.number_errors > 0:
                self.number_errors -= 1
        self.input_text.delete("1.0", tk.END)
        self._update_number_display()
        self.update_number_status_label()
        return True

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
            progress = f"{self.number_index}/{self.number_total_digits}"

        if self.is_blind_mode_active():
            error_text = "Errors: hidden"
        else:
            error_text = f"Errors: {self.number_errors}"

        self.wpm_label.configure(
            text=(
                f"Number mode  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Digits/min: {digits_per_minute:.1f}  |  "
                f"Progress: {progress}  |  "
                f"{error_text}"
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
        typed_digits_text = "".join(self.number_input_history)
        typed_digits_count = len(typed_digits_text)
        blind_end_error_percentage: float | None = None
        if self.is_blind_mode_active() and typed_digits_count > 0:
            if sudden_death:
                total_targets = max(typed_digits_count, 1)
            else:
                total_targets = max(self.number_total_digits, 1)
            target_digits = "".join(self.number_sequence[:total_targets])
            blind_end_error_percentage = calculate_end_error_percentage(
                target_digits,
                typed_digits_text,
                total_targets
            )

        if sudden_death:
            correct_digits = self.number_correct_digits
            if not self.is_blind_mode_active():
                save_sudden_death_number_result(
                    self.sudden_death_number_stats_file_path,
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
                    + (
                        f"  |  End error %: {blind_end_error_percentage:.1f}"
                        if blind_end_error_percentage is not None
                        else ""
                    )
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
                    + (
                        f"  |  End error %: {blind_end_error_percentage:.1f}"
                        if blind_end_error_percentage is not None
                        else ""
                    )
                )
        else:
            total_digits = max(self.number_total_digits, 1)
            error_percentage = (self.number_errors / total_digits) * 100.0
            if not self.is_blind_mode_active():
                save_number_result(
                    self.number_stats_file_path,
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
            if self.is_blind_mode_active():
                if blind_end_error_percentage is not None:
                    error_summary = (
                        f"End error %: {blind_end_error_percentage:.1f}"
                    )
                else:
                    error_summary = "Errors: hidden"
            else:
                error_summary = (
                    f"Errors: {self.number_errors}  |  "
                    f"Error %: {error_percentage:.1f}"
                )
            summary = (
                f"Number mode complete  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Digits/min: {digits_per_minute:.1f}  |  "
                f"{error_summary}"
            )

        target_digits_for_display = "".join(
            self.number_sequence[:len(typed_digits_text)]
        )

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        display_content = (
            f"{display_message}\n\nTarget sequence:\n{target_digits_for_display}"
        )
        self.display_text.insert("1.0", display_content)
        self.display_text.configure(state="disabled")

        self.info_label.configure(text=info_message)
        self.wpm_label.configure(text=summary)

        self._display_sequence_result(
            typed_digits_text,
            target_digits_for_display
        )

        self.is_number_mode = False
        self.start_time = None
        self.number_sequence = []
        self.number_index = 0
        self.number_total_digits = 0
        self.number_errors = 0
        self.number_correct_digits = 0
        self.number_input_history = []
        self.last_session_mode = "number"

        if blind_end_error_percentage is not None:
            save_blind_number_result(
                self.blind_number_stats_file_path,
                digits_per_minute=digits_per_minute,
                typed_digits=typed_digits_count,
                duration_seconds=elapsed_seconds,
                completed=completed_sequence if sudden_death else True,
                end_error_percentage=blind_end_error_percentage,
                is_training_run=self.training_run_var.get()
            )


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
        if self.is_blind_mode_active():
            self._update_blind_target_indicator(len(typed_text))

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
        show_error_tags = not self.is_blind_mode_active()

        correct = 0
        first_error_index: int | None = None

        for index, char in enumerate(typed_text):
            if index >= len(self.target_text):
                if show_error_tags:
                    start = f"1.0 + {index} chars"
                    end = f"1.0 + {index + 1} chars"
                    self.input_text.tag_add("error", start, end)
                if first_error_index is None:
                    first_error_index = index
                continue

            if char != self.target_text[index]:
                if show_error_tags:
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

        typed_text = self.input_text.get("1.0", "end-1c")
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

        blind_end_error_percentage: float | None = None
        if self.is_blind_mode_active():
            blind_end_error_percentage = calculate_end_error_percentage(
                self.target_text,
                typed_text,
                len(self.target_text)
            )

        if not self.is_blind_mode_active():
            save_sudden_death_wpm_result(
                self.sudden_death_typing_stats_file_path,
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
                + (
                    f"  |  End error %: {blind_end_error_percentage:.1f}"
                    if blind_end_error_percentage is not None
                    else ""
                )
            )
        )
        if self.is_blind_mode_active():
            self._update_blind_target_indicator(len(typed_text))
            self._show_blind_final_text(typed_text)
            save_blind_typing_result(
                self.blind_typing_stats_file_path,
                wpm=wpm,
                typed_characters=len(typed_text),
                duration_seconds=elapsed_seconds,
                completed=False,
                end_error_percentage=blind_end_error_percentage or 0.0,
                is_training_run=self.training_run_var.get()
            )


    def update_wpm(self, typed_text: str) -> None:
        if self.start_time is None:
            if self.is_blind_mode_active():
                text = "Time: 0.0 s  |  WPM: 0.0"
            else:
                text = "Time: 0.0 s  |  WPM: 0.0  |  Errors: 0  |  Error %: 0.0"
            self.wpm_label.configure(text=text)
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
                + (
                    "Errors: hidden  |  Error %: hidden"
                    if self.is_blind_mode_active()
                    else f"Errors: {errors}  |  Error %: {error_percentage:.1f}"
                )
            )
        )


    def check_completion(self, typed_text: str) -> None:
        """
        Check whether the user has fully and correctly typed the target text.

        Once the text is completed, the timer is stopped and the result is
        saved to the statistics file.
        """
        final_typed_text = typed_text
        target_length = len(self.target_text)
        if self.is_blind_mode_active():
            if len(typed_text) < target_length:
                return
            typed_text = typed_text[:target_length]
        else:
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

        end_error_percentage: float | None = None
        if self.is_blind_mode_active():
            end_error_percentage = calculate_end_error_percentage(
                self.target_text,
                final_typed_text,
                target_length
            )

        if self.is_sudden_death_active():
            if not self.is_blind_mode_active():
                save_sudden_death_wpm_result(
                    self.sudden_death_typing_stats_file_path,
                    wpm,
                    target_length,
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
                    f"WPM: {wpm:.1f}  |  Correct chars: {target_length}"
                    + (
                        f"  |  End error %: {end_error_percentage:.1f}"
                        if end_error_percentage is not None
                        else ""
                    )
                )
            )
            if self.is_blind_mode_active():
                self._update_blind_target_indicator(target_length)
                self._show_blind_final_text(final_typed_text)
                save_blind_typing_result(
                    self.blind_typing_stats_file_path,
                    wpm=wpm,
                    typed_characters=len(final_typed_text),
                    duration_seconds=elapsed_seconds,
                    completed=True,
                    end_error_percentage=end_error_percentage or 0.0,
                    is_training_run=self.training_run_var.get()
                )
        else:
            if not self.is_blind_mode_active():
                save_wpm_result(
                    self.stats_file_path,
                    wpm,
                    error_percentage,
                    elapsed_seconds,
                    self.training_run_var.get()
                )
            if self.is_blind_mode_active():
                self._show_blind_final_text(final_typed_text)
                save_blind_typing_result(
                    self.blind_typing_stats_file_path,
                    wpm=wpm,
                    typed_characters=len(final_typed_text),
                    duration_seconds=elapsed_seconds,
                    completed=True,
                    end_error_percentage=end_error_percentage or 0.0,
                    is_training_run=self.training_run_var.get()
                )

            if self.is_blind_mode_active():
                summary = (
                    f"Typing complete  |  Time: {elapsed_seconds:.1f} s  |  "
                    f"WPM: {wpm:.1f}  |  End error %: {end_error_percentage or 0.0:.1f}"
                )
            else:
                summary = (
                    f"Typing complete  |  Time: {elapsed_seconds:.1f} s  |  "
                    f"WPM: {wpm:.1f}  |  Errors: {errors}  |  "
                    f"Error %: {error_percentage:.1f}"
                )
            self.wpm_label.configure(text=summary)


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
