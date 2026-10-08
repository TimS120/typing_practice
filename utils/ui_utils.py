"""
Typing trainer with live words per minute feedback.

This module provides a Tkinter based typing trainer. It loads a list of
training texts from a file, allows the user to select a text, and then measures
the words per minute (WPM) while the user types. Completed session WPM values
are stored in a statistics file and can be visualized.
"""

from __future__ import annotations

import random
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, List
import ctypes
from ctypes import wintypes
import sys
from concurrent.futures import ThreadPoolExecutor

from .system_theme import system_prefers_dark
from .text_manager import TextManager
from .typing_input import normalize_wrapped_input
from .keyboard_layouts import LAYOUTS, DEFAULT_LAYOUT, layout_characters, drill_characters


import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

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
    get__file_path,
    load_settings,
    save_settings,
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
SPECIAL_SEQUENCE_LENGTH = 100
NUMBER_SEQUENCE_LENGTH = 100
TARGET_TEXT_DISPLAY_WIDTH = 90
LIGHT_THEME = {
    "background": "#f4f6fb",
    "surface": "#ffffff",
    "text": "#111827",
    "muted_text": "#4b5563",
    "accent": "#3b82f6",
    "button_background": "#e4e8f1",
    "button_foreground": "#111827",
    "button_active_background": "#d4dae6",
    "input_background": "#ffffff",
    "input_foreground": "#111827",
    "select_background": "#dbeafe",
    "select_foreground": "#0f172a",
    "error_background": "#e60000",
    "error_foreground": "#FFFFFF",
    "border": "#d1d5db",
    "titlebar_color": "#f4f6fb",
    "titlebar_text": "#111827",
    "titlebar_border": "#d1d5db",
    "blind_highlight": "#e5e7eb",
    "blind_mask_foreground": "#ffffff",
    "tab_background": "#e5e7eb",
    "tab_foreground": "#4b5563",
    "tab_active_background": "#ffffff",
    "tab_active_foreground": "#111827",
    "tab_border": "#d1d5db",
    "combobox_background": "#ffffff",
    "combobox_foreground": "#111827",
    "combobox_border": "#cfd5e3",
}
DARK_THEME = {
    "background": "#0d1117",
    "surface": "#161b22",
    "text": "#f4f6fb",
    "muted_text": "#a5b4c3",
    "accent": "#60a5fa",
    "button_background": "#1f2430",
    "button_foreground": "#f4f6fb",
    "button_active_background": "#2b3240",
    "input_background": "#11141b",
    "input_foreground": "#f4f6fb",
    "select_background": "#1e3a8a",
    "select_foreground": "#f4f6fb",
    "error_background": "#e60000",
    "error_foreground": "#fecaca",
    "border": "#252c36",
    "titlebar_color": "#0d1117",
    "titlebar_text": "#f4f6fb",
    "titlebar_border": "#1f2630",
    "blind_highlight": "#2b3240",
    "blind_mask_foreground": "#161b22",
    "tab_background": "#11141b",
    "tab_foreground": "#94a3b8",
    "tab_active_background": "#1f2430",
    "tab_active_foreground": "#f4f6fb",
    "tab_border": "#1f2630",
    "combobox_background": "#161b22",
    "combobox_foreground": "#f4f6fb",
    "combobox_border": "#2f3543",
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

    def __init__(self, master: tk.Tk, texts: list[dict[str, str]]) -> None:
        """
        Initialize the GUI and internal state.

        :param master: Root Tkinter window.
        :param texts: List of training texts.
        """
        self.master = master
        self.text_entries = texts
        self.texts = [entry["text"] for entry in texts]
        self.settings = load_settings()
        self.keyboard_layout_var = tk.StringVar(master, value=self.settings.get("keyboard_layout", DEFAULT_LAYOUT))
        self.custom_characters = self.settings.get("custom_characters", LAYOUTS[DEFAULT_LAYOUT])
        self.coverage_threshold = self.settings.get("coverage_threshold", 10)
        self.text_manager = None
        self._loaded_typing_text = ""
        self._helper_kind = None
        self._theme_job = None
        self._settings_job = None
        self._theme_future = None
        self._theme_executor = ThreadPoolExecutor(max_workers=1)

        self.selected_text: str = ""
        self.target_text: str = ""
        self._soft_wrap_boundaries: set[int] = set()
        self._wraps_captured = False
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

        self.current_font_size: int = self.settings.get("font_size", DEFAULT_FONT_SIZE)
        self.text_font: tkfont.Font | None = None
        self.ui_font_size = self.settings.get("ui_font_size", 10)
        self.ui_font = tkfont.Font(family=tkfont.nametofont("TkDefaultFont").actual("family"),
                                  size=self.ui_font_size)
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
        self.theme_var = tk.StringVar(master=self.master, value=self.settings.get("theme", "system").title())
        self.dark_mode_enabled = (self._detect_system_dark_mode() if self.theme_var.get() == "System"
                                  else self.theme_var.get() == "Dark")
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
        self.master.protocol("WM_DELETE_WINDOW", self.close)
        self.master.bind("<Configure>", self._on_window_resize, add="+")
        self._theme_job = self.master.after(2000, self._poll_system_theme)


    def _build_gui(self) -> None:
        self.master.title("Typing Trainer")
        self.master.geometry(self.settings.get("window_size", GUI_WINDOW_XY))
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.info_text_var = tk.StringVar(self.master)
        self.description_var = tk.StringVar(self.master)
        self.stats_summary_var = tk.StringVar(self.master, value="Time: 0.0 s  |  WPM: 0.0")
        self.practice_type_var = tk.StringVar(self.master, value="typing")
        self.stats_mode_var = tk.StringVar(self.master, value="Standard")
        self.display_text_widgets = {}
        self.input_text_widgets = {}
        self.text_font = tkfont.Font(family=DEFAULT_FONT_FAMILY, size=self.current_font_size)

        main = ttk.Frame(self.master, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)
        self.app_tabs = ttk.Notebook(main)
        self.app_tabs.grid(row=0, column=0, sticky="nsew")
        self.practice_page = ttk.Frame(self.app_tabs, padding=10)
        self.text_management_page = ttk.Frame(self.app_tabs)
        self.statistics_page = ttk.Frame(self.app_tabs, padding=14)
        self.settings_page = ttk.Frame(self.app_tabs, padding=18)
        self.app_tabs.add(self.practice_page, text="Typing")
        self.app_tabs.add(self.text_management_page, text="Text management")
        self.app_tabs.add(self.statistics_page, text="Statistics")
        self.app_tabs.add(self.settings_page, text="Settings")
        self.app_tabs.bind("<<NotebookTabChanged>>", self._on_main_tab_changed)
        self._build_settings_page()
        practice = self.practice_page
        practice.columnconfigure(0, weight=1)
        practice.rowconfigure(2, weight=1)

        controls = ttk.Frame(practice)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for label, key in (("Typing text", "typing"), ("Helper modes", "helper")):
            ttk.Radiobutton(controls, text=label, variable=self.practice_type_var, value=key,
                            style="Practice.TRadiobutton",
                            command=lambda key=key: self._choose_practice(key)).pack(side="left", padx=(0, 6))
        ttk.Label(controls, text="Mode").pack(side="left", padx=(18, 6))
        self.sudden_death_mode_combobox = ttk.Combobox(
            controls, textvariable=self.sudden_death_mode_var,
            values=[label for _, label in SUDDEN_DEATH_MODE_OPTIONS], state="readonly", width=14,
            font=self.ui_font)
        self.sudden_death_mode_combobox.pack(side="left")
        self.sudden_death_mode_combobox.bind("<<ComboboxSelected>>", self.on_sudden_death_mode_change)
        self.training_toggle = ttk.Checkbutton(controls, text="Training run", variable=self.training_run_var,
                                              command=self._refresh_mode_description)
        self.training_toggle.pack(side="left", padx=(18, 0))

        information = ttk.Frame(practice, style="Info.TFrame", padding=(10, 8))
        information.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        information.columnconfigure(1, weight=1)
        ttk.Label(information, text="ⓘ", style="Info.TLabel").grid(row=0, column=0, sticky="n", padx=(0, 8))
        self.description_label = ttk.Label(information, textvariable=self.description_var,
                                           style="Info.TLabel", wraplength=1000)
        self.description_label.grid(row=0, column=1, sticky="ew")
        information.bind("<Configure>", lambda event: self.description_label.configure(
            wraplength=max(180, event.width - 55)))

        self.tab_control = ttk.Notebook(practice, style="Practice.TNotebook")
        self.tab_control.grid(row=2, column=0, sticky="nsew")
        typing = ttk.Frame(self.tab_control)
        helper = ttk.Frame(self.tab_control)
        self.tab_control.add(typing, text="Typing text")
        self.tab_control.add(helper, text="Helper modes")
        for page in (typing, helper):
            page.columnconfigure(0, weight=1)
            page.rowconfigure(1, weight=1)
        self._tab_frames = {"typing": typing, "helper": helper}

        typing_content = ttk.Frame(typing)
        typing_content.grid(row=1, column=0, sticky="nsew")
        typing_content.columnconfigure(1, weight=1)
        typing_content.rowconfigure(0, weight=1)
        library = ttk.Frame(typing_content, padding=(0, 0, 10, 0))
        library.grid(row=0, column=0, sticky="nsew")
        library.columnconfigure(0, weight=1)
        library.rowconfigure(1, weight=1)
        ttk.Label(library, text="Available texts").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.text_listbox = tk.Listbox(library, width=25, height=12, exportselection=False, font=self.ui_font)
        self.text_listbox.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(library, command=self.text_listbox.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.text_listbox.configure(yscrollcommand=scroll.set)
        self.refresh_text_list()
        self.text_listbox.bind("<<ListboxSelect>>", self.on_load_selected)
        actions = ttk.Frame(library)
        actions.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        for label, command in (("Load random", self.on_load_random),):
            ttk.Button(actions, text=label, command=command).pack(fill="x", pady=2)
        self._build_practice_input(typing_content, "typing", column=1)

        drill_controls = ttk.Frame(helper)
        drill_controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for label, command in (("Letters", self.start_letter_mode), ("Characters", self.start_special_mode),
                               ("Numbers", self.start_number_mode)):
            ttk.Button(drill_controls, text=label, command=command).pack(side="left", padx=(0, 6))
        self._build_practice_input(helper, "helper", row=1)

        status = ttk.Frame(practice)
        status.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        status.columnconfigure(0, weight=1)
        self.info_label = ttk.Label(status, textvariable=self.info_text_var, wraplength=800)
        self.info_label.grid(row=0, column=0, sticky="w")
        self.wpm_label = ttk.Label(status, textvariable=self.stats_summary_var)
        self.wpm_label.grid(row=1, column=0, sticky="w", pady=(3, 0))
        status.bind("<Configure>", lambda event: self.info_label.configure(wraplength=max(180, event.width)))

        self._build_statistics_page()
        self._active_tab_key = "typing"
        self.display_text = self.display_text_widgets["typing"]
        self.input_text = self.input_text_widgets["typing"]
        self.tab_control.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.text_manager = TextManager(self, parent=self.text_management_page)
        self._refresh_mode_description(update_status=True)
        self._apply_theme()

    def _build_settings_page(self):
        viewport = self.settings_page
        viewport.columnconfigure(0, weight=1)
        viewport.rowconfigure(0, weight=1)
        self.settings_canvas = tk.Canvas(viewport, highlightthickness=0)
        self.settings_canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(viewport, command=self.settings_canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.settings_canvas.configure(yscrollcommand=scroll.set)
        page = ttk.Frame(self.settings_canvas)
        content = self.settings_canvas.create_window((0, 0), window=page, anchor="nw")
        page.bind("<Configure>", lambda event: self.settings_canvas.configure(scrollregion=self.settings_canvas.bbox("all")))
        self.settings_canvas.bind("<Configure>", lambda event: self.settings_canvas.itemconfigure(content, width=event.width))
        page.columnconfigure(0, weight=1)
        theme = ttk.LabelFrame(page, text="Theme", padding=14)
        theme.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(theme, text="System follows your desktop appearance. Light and Dark override it.",
                  wraplength=750).pack(anchor="w", pady=(0, 10))
        choices = ttk.Frame(theme)
        choices.pack(anchor="w")
        for value in ("System", "Light", "Dark"):
            ttk.Radiobutton(choices, text=value, value=value, variable=self.theme_var,
                            style="Practice.TRadiobutton", command=self.change_theme).pack(side="left", padx=(0, 6))
        self.practice_font_size_var = tk.StringVar(self.master)
        self.ui_font_size_var = tk.StringVar(self.master)
        for row, title, explanation, variable, smaller, reset, bigger in (
                (1, "Practice text size", "Size of practice passages and the text-manager editor.",
                 self.practice_font_size_var, self.decrease_font_size, self.reset_font_size, self.increase_font_size),
                (2, "UI text size", "Size of labels, buttons, tabs, pickers and text names.",
                 self.ui_font_size_var, lambda: self.change_ui_font_size(-1), self.reset_ui_font_size,
                 lambda: self.change_ui_font_size(1))):
            group = ttk.LabelFrame(page, text=title, padding=14)
            group.grid(row=row, column=0, sticky="ew", pady=(0, 14))
            ttk.Label(group, text=explanation, wraplength=750).pack(anchor="w", pady=(0, 10))
            controls = ttk.Frame(group)
            controls.pack(anchor="w")
            ttk.Label(controls, textvariable=variable, width=7).pack(side="left", padx=(0, 12))
            for label, command in (("Smaller", smaller), ("Reset", reset), ("Larger", bigger)):
                ttk.Button(controls, text=label, command=command).pack(side="left", padx=(0, 6))
        keyboard = ttk.LabelFrame(page, text="Keyboard layout", padding=14)
        keyboard.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(keyboard, text="Determines coverage characters and the Letters / Characters / Numbers drill sets. "
                  "Text languages do not filter coverage.", wraplength=750).pack(anchor="w", pady=(0, 10))
        picker = ttk.Combobox(keyboard, textvariable=self.keyboard_layout_var,
                              values=(*LAYOUTS, "Custom"), state="readonly", font=self.ui_font, width=24)
        picker.pack(anchor="w")
        picker.bind("<<ComboboxSelected>>", self.change_keyboard_layout)
        ttk.Label(keyboard, text="Custom characters (case-sensitive; Enter and Tab may be included). "
                  "Apply to use this set; repeated characters count once.", wraplength=750).pack(anchor="w", pady=(10, 4))
        self.custom_characters_editor = tk.Text(keyboard, height=4, wrap="char", font=self.text_font)
        self.custom_characters_editor.pack(fill="x")
        self.custom_characters_editor.insert("1.0", self.custom_characters)
        ttk.Button(keyboard, text="Apply custom characters", command=self.apply_custom_characters).pack(anchor="w", pady=(8, 0))
        self.layout_status = tk.StringVar(page)
        ttk.Label(keyboard, textvariable=self.layout_status, wraplength=750).pack(anchor="w", pady=(8, 0))
        self.layout_status.set(f"{len(self.get_layout_characters())} distinct characters in the selected layout.")
        ttk.Label(page, text="Changes are applied and saved automatically, except custom character edits.", wraplength=750).grid(
            row=4, column=0, sticky="w")
        self._update_settings_labels()
        def scroll_settings(event):
            if self.settings_canvas.yview() == (0.0, 1.0):
                return
            direction = (-1 if event.num == 4 else 1) if event.num in (4, 5) else (-1 if event.delta > 0 else 1)
            self.settings_canvas.yview_scroll(direction * 3, "units")
            return "break"
        def bind_scroll(widget):
            for event in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                widget.bind(event, scroll_settings, add="+")
            for child in widget.winfo_children():
                bind_scroll(child)
        bind_scroll(viewport)

    def get_layout_characters(self):
        return layout_characters(self.keyboard_layout_var.get(), self.custom_characters)

    def change_keyboard_layout(self, event=None):
        # Sequences already in progress retain their captured character set.
        self.layout_status.set(f"{len(self.get_layout_characters())} distinct characters. New drills use this layout.")
        self._save_preferences()
        if self.text_manager is not None:
            self.text_manager.refresh_coverage()

    def apply_custom_characters(self):
        characters = self.custom_characters_editor.get("1.0", "end-1c")
        if not characters:
            self.layout_status.set("Enter at least one character before applying a custom layout.")
            return
        self.custom_characters = "".join(dict.fromkeys(characters))
        self.keyboard_layout_var.set("Custom")
        self.change_keyboard_layout()

    def _prepare_drill_characters(self, kind):
        characters = drill_characters(self.get_layout_characters(), kind)
        if not characters:
            messagebox.showinfo("Keyboard layout", f"The selected layout has no characters for the {kind} drill.", parent=self.master)
            return False
        self._drill_characters = characters
        return True

    def _update_settings_labels(self):
        self.practice_font_size_var.set(f"{self.current_font_size} pt")
        self.ui_font_size_var.set(f"{self.ui_font_size} pt")

    def _build_practice_input(self, parent, key, row=0, column=0):
        area = ttk.Frame(parent)
        area.grid(row=row, column=column, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.rowconfigure(1, weight=1)
        area.rowconfigure(3, weight=1)
        ttk.Label(area, text="Text to type" if key == "typing" else "Character to type").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        target = tk.Text(area, height=5, width=TARGET_TEXT_DISPLAY_WIDTH, wrap="word",
                         state="disabled", font=self.text_font)
        target.grid(row=1, column=0, sticky="nsew")
        target_scroll = ttk.Scrollbar(area, command=target.yview)
        target_scroll.grid(row=1, column=1, sticky="ns")
        target.configure(yscrollcommand=target_scroll.set)
        for event in ("<<Copy>>", "<Control-c>", "<Control-C>", "<Command-c>", "<Command-C>", "<Control-Insert>"):
            target.bind(event, self._block_target_copy)
        input_header = ttk.Frame(area)
        input_header.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        ttk.Label(input_header, text="Your input").pack(side="left")
        ttk.Button(input_header, text="Reset session", command=self.handle_reset_button).pack(side="right")
        typed = tk.Text(area, height=6, wrap="word", font=self.text_font)
        typed.grid(row=3, column=0, sticky="nsew")
        input_scroll = ttk.Scrollbar(area, command=typed.yview)
        input_scroll.grid(row=3, column=1, sticky="ns")
        typed.configure(yscrollcommand=input_scroll.set)
        typed.bind("<Key>", self.on_key_press)
        if key == "typing":
            typed.bind("<<Modified>>", self._on_typing_input_changed)
        self.display_text_widgets[key] = target
        self.input_text_widgets[key] = typed

    def _build_statistics_page(self):
        viewport = self.statistics_page
        viewport.columnconfigure(0, weight=1)
        viewport.rowconfigure(0, weight=1)
        self.stats_canvas = tk.Canvas(viewport, highlightthickness=0)
        self.stats_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(viewport, command=self.stats_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.stats_canvas.configure(yscrollcommand=scrollbar.set)
        page = ttk.Frame(self.stats_canvas)
        content = self.stats_canvas.create_window((0, 0), window=page, anchor="nw")
        page.bind("<Configure>", lambda event: self.stats_canvas.configure(scrollregion=self.stats_canvas.bbox("all")))
        page.columnconfigure(0, weight=1)
        filters = ttk.Frame(page)
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ttk.Label(filters, text="Chart mode").pack(side="left", padx=(0, 6))
        self.stats_mode_selector = ttk.Combobox(filters, textvariable=self.stats_mode_var, state="readonly",
                                               values=[label for _, label in SUDDEN_DEATH_MODE_OPTIONS],
                                               width=14, font=self.ui_font)
        self.stats_mode_selector.pack(side="left")
        self.stats_mode_selector.bind("<<ComboboxSelected>>", lambda event: event.widget.selection_clear())
        ttk.Label(filters, text="Runs").pack(side="left", padx=(24, 6))
        self.stats_filter_combobox = ttk.Combobox(filters, textvariable=self.stats_filter_var, state="readonly",
                                                values=[label for _, label in STATS_FILTER_OPTIONS],
                                                width=18, font=self.ui_font)
        self.stats_filter_combobox.pack(side="left")
        intro = ttk.Label(page, text="Choose a chart to review your practice. Filters affect the saved results, not your next exercise.",
                          wraplength=900)
        intro.grid(row=1, column=0, sticky="w", pady=(0, 14))
        cards = ttk.Frame(page)
        cards.grid(row=2, column=0, sticky="ew")
        for col in range(2):
            cards.columnconfigure(col, weight=1, uniform="cards")
        card_contents = []
        for index, (title, description, command) in enumerate((
                ("Typing text", "Words per minute, accuracy and typing duration.", self.show_stats),
                ("Letters", "Letters per minute and accuracy for letter drills.", self.show_letter_stats),
                ("Characters", "Symbol speed and accuracy for character drills.", self.show_special_stats),
                ("Numbers", "Digits per minute and accuracy for number drills.", self.show_number_stats),
                ("Overview", "Trends and activity across all modes and sub-modes; uses the Runs filter.", self.show_general_stats))):
            card = ttk.LabelFrame(cards, text=title, padding=12)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=5, pady=5)
            label = ttk.Label(card, text=description, wraplength=400)
            label.pack(anchor="w", pady=(0, 8))
            card_contents.append((card, label))
            ttk.Button(card, text="Open chart", command=command).pack(anchor="w")

        def resize_statistics(event):
            self.stats_canvas.itemconfigure(content, width=event.width)
            intro.configure(wraplength=max(180, event.width - 20))
            columns = 1 if event.width < 850 else 2
            cards.columnconfigure(1, weight=1 if columns == 2 else 0, uniform="cards" if columns == 2 else "")
            for index, (card, label) in enumerate(card_contents):
                card.grid_configure(row=index // columns, column=index % columns)
                label.configure(wraplength=max(180, event.width // columns - 70))
        self.stats_canvas.bind("<Configure>", resize_statistics)

        def scroll(event):
            if self.stats_canvas.yview() == (0.0, 1.0):
                return
            direction = (-1 if event.num == 4 else 1) if event.num in (4, 5) else (-1 if event.delta > 0 else 1)
            self.stats_canvas.yview_scroll(direction * 3, "units")
            return "break"

        def bind_scroll(widget):
            for event in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                widget.bind(event, scroll, add="+")
            for child in widget.winfo_children():
                bind_scroll(child)
        bind_scroll(viewport)

    def _choose_practice(self, key):
        self.app_tabs.select(self.practice_page)
        self.tab_control.select(self._tab_frames[key])
        self._set_active_tab(key)

    def _on_main_tab_changed(self, event=None):
        if self.app_tabs.select() == str(self.text_management_page) and self.text_manager is None:
            self.text_manager = TextManager(self, parent=self.text_management_page)

    def _get_plot_mode_key(self):
        return SUDDEN_DEATH_MODE_KEY_BY_LABEL.get(self.stats_mode_var.get(), "standard")

    def _refresh_mode_description(self, update_status=False):
        mode = self._get_sudden_death_mode_key()
        if self._active_tab_key == "typing":
            title = "Typing text"
            instruction = "Click a text to load it, then type it. Enter is optional at automatic wraps; saved newlines require Enter."
        else:
            names = {"letter": "Letters", "special": "Characters", "number": "Numbers"}
            title = names.get(self._helper_kind, "Helper modes")
            instruction = {
                "letter": "Type each letter shown, matching uppercase and lowercase. A new letter follows each entry.",
                "special": "Type each punctuation mark or special character shown. A new character follows each entry.",
                "number": "Type each digit shown; you can use the numeric keypad. A new digit follows each entry."
            }.get(self._helper_kind, "Choose Letters, Characters or Numbers to start a drill.")
        behavior = {
            "standard": "Standard: errors are highlighted; aim for accuracy." if self._active_tab_key == "typing"
                        else "Standard: practise a sequence of 100 characters with visible error feedback.",
            "sudden": "Sudden death: the first mistake ends the run." +
                      (" Keep your streak going as long as you can." if self._active_tab_key == "helper" else ""),
            "blind": "Blind mode: your input and live error feedback are hidden; review accuracy when the run ends." +
                     (" Complete 100 characters." if self._active_tab_key == "helper" else "")
        }[mode]
        run = "Training run: saved separately from benchmarks." if self.training_run_var.get() else "Benchmark run."
        self.description_var.set(f"{title} · {behavior} {instruction} {run}")
        if update_status:
            if self._active_tab_key == "typing":
                self.info_text_var.set("Ready to type. Timing starts with the first character." if self.target_text
                                       else "Load a text to begin." if self.texts
                                       else "No texts yet. Add a passage in Text management.")
            else:
                self.info_text_var.set("Choose a helper drill to begin.")

    def _on_tab_changed(self, event: tk.Event) -> None:
        """
        Adjust layout whenever the notebook tab selection changes.
        """
        tab_id = self.tab_control.select()
        for key, frame in self._tab_frames.items():
            if str(frame) == tab_id:
                self._set_active_tab(key)
                break

    def _set_active_tab(self, tab_key: str) -> None:
        if tab_key == self._active_tab_key:
            self.practice_type_var.set(tab_key)
            self._refresh_mode_description()
            return
        # A practice-type switch starts a fresh run instead of carrying a
        # helper drill's input handling and instructions into text typing.
        self.reset_session()
        self._active_tab_key = tab_key
        self.practice_type_var.set(tab_key)
        self.display_text = self.display_text_widgets[tab_key]
        self.input_text = self.input_text_widgets[tab_key]
        if tab_key == "typing":
            self.selected_text = self._loaded_typing_text
            self._apply_loaded_text()
        else:
            self._helper_kind = None
            self.reset_session(clear_display=True)
        self._refresh_mode_description(update_status=True)
        self._update_input_visibility()
        self._update_blind_target_indicator()

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
        self._update_settings_labels()
        self._save_preferences()

    def refresh_text_list(self) -> None:
        self.texts = [entry["text"] for entry in self.text_entries]
        self.text_listbox.delete(0, tk.END)
        for index, entry in enumerate(self.text_entries, 1):
            self.text_listbox.insert(tk.END, f"{index:02d}  {entry['name']}")

    def open_text_manager(self) -> None:
        if self.text_manager is None:
            self.text_manager = TextManager(self, parent=self.text_management_page)
        self.app_tabs.select(self.text_management_page)

    def change_ui_font_size(self, delta):
        self.ui_font_size = max(8, min(24, self.ui_font_size + delta))
        self.ui_font.configure(size=self.ui_font_size)
        self._update_settings_labels()
        self._save_preferences()

    def reset_ui_font_size(self):
        self.ui_font_size = 10
        self.ui_font.configure(size=self.ui_font_size)
        self._update_settings_labels()
        self._save_preferences()

    def change_theme(self, event=None) -> None:
        preference = self.theme_var.get().lower()
        self.dark_mode_enabled = (self._detect_system_dark_mode() if preference == "system"
                                  else preference == "dark")
        self._apply_theme()
        self._update_settings_labels()
        self._save_preferences()

    def _poll_system_theme(self) -> None:
        if self.theme_var.get() == "System":
            if self._theme_future is None:
                self._theme_future = self._theme_executor.submit(self._detect_system_dark_mode)
            elif self._theme_future.done():
                dark = self._theme_future.result()
                self._theme_future = None
                if dark != self.dark_mode_enabled:
                    self.dark_mode_enabled = dark
                    self._apply_theme()
        self._theme_job = self.master.after(1000, self._poll_system_theme)

    def _on_window_resize(self, event) -> None:
        if event.widget is self.master:
            if self._settings_job is not None:
                self.master.after_cancel(self._settings_job)
            self._settings_job = self.master.after(400, self._save_preferences)

    def _save_preferences(self) -> None:
        if self._settings_job is not None:
            self.master.after_cancel(self._settings_job)
        self._settings_job = None
        save_settings({"theme": self.theme_var.get().lower(),
                       "font_size": self.current_font_size,
                       "ui_font_size": self.ui_font_size,
                       "keyboard_layout": self.keyboard_layout_var.get(),
                       "custom_characters": self.custom_characters,
                       "coverage_threshold": self.coverage_threshold,
                       "window_size": f"{self.master.winfo_width()}x{self.master.winfo_height()}"})

    def close(self) -> None:
        if self.text_manager is not None and self.text_manager.window.winfo_exists():
            if not self.text_manager.close():
                return
        try:
            self._save_preferences()
        except OSError as error:
            messagebox.showerror("Settings", f"Could not save settings: {error}", parent=self.master)
            return
        for job in (self._theme_job, self._settings_job, self._title_bar_refresh_job, self.update_job_id):
            if job is not None:
                self.master.after_cancel(job)
        self._theme_executor.shutdown(wait=False, cancel_futures=True)
        self.master.destroy()


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
        if self._active_tab_key == "helper" and self._helper_kind:
            {"letter": self.start_letter_mode, "special": self.start_special_mode,
             "number": self.start_number_mode}[self._helper_kind]()
        self._refresh_mode_description(update_status=self._active_tab_key == "typing" or not self._helper_kind)
        self._update_input_visibility()
        self._update_blind_target_indicator()
        if self.sudden_death_mode_combobox is not None:
            self.sudden_death_mode_combobox.selection_clear()

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
            self.info_text_var.set(
                "Sudden death enabled. Load a text or start a mode."
            )
        else:
            self.info_text_var.set(
                "Sudden death disabled. Normal sessions restored."
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
            typed_length = len(self._read_typing_input()[0])
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

        normalized, offsets = self._read_typing_input()
        self.highlight_errors(normalized, offsets)
        self.input_text.see("end")

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
        self.finished = True
        self.input_text.configure(state="disabled")

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

        self.style.configure(".", font=self.ui_font)
        self.style.layout("Practice.TNotebook.Tab", [])
        self.style.configure("Practice.TNotebook", tabmargins=0, padding=0)
        self.style.layout("Practice.TRadiobutton", [("Radiobutton.padding", {
            "sticky": "nswe", "children": [("Radiobutton.label", {"sticky": "nswe"})]})])
        self.style.configure("Practice.TRadiobutton", padding=(12, 7),
                             background=theme["button_background"], foreground=theme["text"])
        self.style.map("Practice.TRadiobutton", background=[("selected", theme["select_background"]),
                                                              ("active", theme["button_active_background"])])
        self.style.configure("Info.TFrame", background=theme["select_background"])
        self.style.configure("Info.TLabel", background=theme["select_background"], foreground=theme["text"])
        self.stats_canvas.configure(background=theme["background"])
        self.settings_canvas.configure(background=theme["background"])
        self.custom_characters_editor.configure(bg=theme["input_background"], fg=theme["text"],
            insertbackground=theme["text"], selectbackground=theme["select_background"],
            selectforeground=theme["select_foreground"])
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
            foreground=theme["button_foreground"],
            bordercolor=theme["border"], lightcolor=theme["border"], darkcolor=theme["border"]
        )
        self.style.map(
            "TButton",
            background=[
                ("pressed", theme["button_active_background"]),
                ("active", theme["button_active_background"])
            ],
            foreground=[("disabled", theme["muted_text"]), ("active", theme["button_foreground"])],
            bordercolor=[("active", theme["border"])],
            lightcolor=[("active", theme["button_active_background"])],
            darkcolor=[("active", theme["button_active_background"])]
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
        self.style.map(
            "TCheckbutton",
            background=[("active", theme["background"]), ("selected", theme["background"])],
            foreground=[("disabled", theme["muted_text"]), ("active", theme["text"])],
            indicatorbackground=[("selected", theme["accent"]), ("active", theme["button_active_background"])],
            indicatorforeground=[("selected", theme["background"])]
        )
        self.style.configure("TCheckbutton", indicatorbackground=theme["button_background"],
                             indicatorforeground=theme["text"])
        self.style.configure("TScrollbar", background=theme["button_background"],
                             troughcolor=theme["surface"], arrowcolor=theme["text"],
                             bordercolor=theme["border"], lightcolor=theme["border"], darkcolor=theme["border"])
        self.style.map("TScrollbar", background=[("active", theme["button_active_background"]),
                                                ("pressed", theme["button_active_background"])])
        self.style.configure("Coverage.Treeview", background=theme["surface"],
                             fieldbackground=theme["surface"], foreground=theme["text"],
                             bordercolor=theme["border"], lightcolor=theme["border"],
                             darkcolor=theme["border"], font=self.ui_font,
                             rowheight=max(24, self.ui_font.metrics("linespace") + 8))
        self.style.map("Coverage.Treeview",
                       background=[("selected", theme["select_background"])],
                       foreground=[("selected", theme["select_foreground"])])
        self.style.configure("Coverage.Treeview.Heading", background=theme["button_background"],
                             foreground=theme["text"], bordercolor=theme["border"],
                             lightcolor=theme["border"], darkcolor=theme["border"], font=self.ui_font)
        self.style.map("Coverage.Treeview.Heading",
                       background=[("pressed", theme["button_active_background"]),
                                   ("active", theme["button_active_background"])],
                       foreground=[("active", theme["text"])],
                       lightcolor=[("active", theme["border"])],
                       darkcolor=[("active", theme["border"])])
        self.style.configure("TEntry", fieldbackground=theme["input_background"],
                             foreground=theme["text"], insertcolor=theme["text"])
        self.style.map("TEntry", fieldbackground=[("readonly", theme["input_background"])])
        self.style.configure(
            "TNotebook",
            background=theme["background"],
            bordercolor=theme["tab_border"],
            borderwidth=0,
            padding=0,
            tabmargins=(0, 6, 0, 0)
        )
        self.style.configure(
            "TNotebook.Tab",
            background=theme["tab_background"],
            foreground=theme["tab_foreground"],
            padding=(14, 6),
            borderwidth=0
        )
        self.style.map(
            "TNotebook.Tab",
            background=[
                ("selected", theme["tab_active_background"]),
                ("active", theme["tab_active_background"])
            ],
            foreground=[
                ("selected", theme["tab_active_foreground"]),
                ("active", theme["tab_active_foreground"])
            ],
            bordercolor=[
                ("selected", theme["tab_border"]),
                ("active", theme["tab_border"])
            ]
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=theme["combobox_background"],
            background=theme["combobox_background"],
            foreground=theme["combobox_foreground"],
            arrowcolor=theme["muted_text"],
            bordercolor=theme["combobox_border"],
            lightcolor=theme["combobox_border"],
            darkcolor=theme["combobox_border"],
            padding=4
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", theme["combobox_background"]),
                ("disabled", theme["background"])
            ],
            foreground=[
                ("readonly", theme["combobox_foreground"]),
                ("disabled", theme["muted_text"])
            ],
            background=[
                ("readonly", theme["combobox_background"]),
                ("disabled", theme["background"])
            ]
        )

        for option, value in (("background", theme["surface"]), ("foreground", theme["text"]),
                              ("selectBackground", theme["select_background"]),
                              ("selectForeground", theme["select_foreground"])):
            self.master.option_add(f"*TCombobox*Listbox.{option}", value)

        # Classic Tk widgets require manual configuration.
        for display in self.display_text_widgets.values():
            display.configure(
                background=theme["surface"],
                foreground=theme["text"],
                insertbackground=theme["text"],
                highlightbackground=theme["border"],
                highlightcolor=theme["accent"],
                selectbackground=theme["select_background"],
                selectforeground=theme["select_foreground"]
            )
            display.tag_configure(
                BLIND_CURSOR_TAG,
                background=theme["blind_highlight"],
                foreground=theme["text"]
            )
        for input_widget in self.input_text_widgets.values():
            input_widget.configure(
                background=theme["input_background"],
                foreground=theme["input_foreground"],
                insertbackground=theme["text"],
                highlightbackground=theme["border"],
                highlightcolor=theme["accent"],
                selectbackground=theme["select_background"],
                selectforeground=theme["select_foreground"]
            )
            input_widget.tag_configure(
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
        if self.text_manager is not None and self.text_manager.window.winfo_exists():
            self.text_manager.apply_theme(theme)
        self._apply_title_bar_colors(theme)
        self._schedule_title_bar_refresh()
        self._update_input_visibility()
        self._update_blind_target_indicator()

    def _detect_system_dark_mode(self) -> bool:
        return system_prefers_dark()


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







    def on_load_selected(self, event=None) -> None:
        """
        Load the text that is currently selected in the listbox.
        """
        selection = self.text_listbox.curselection()
        if not selection:
            if event is not None:
                return
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

        self.app_tabs.select(self.practice_page)
        self._choose_practice("typing")
        self.selected_text = self.texts[index]
        self._loaded_typing_text = self.selected_text

        self._apply_loaded_text()


    def _apply_loaded_text(self) -> None:
        """
        Display the selected text and reset the typing session.
        """
        self.target_text = self.selected_text

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        self.display_text.insert("1.0", self.target_text)
        self.display_text.configure(state="disabled")
        self._update_blind_target_indicator(0)

        self.info_text_var.set(
            "Ready to type. Timing starts with the first character."
        )

        self.reset_session(clear_display=False)
        self._refresh_mode_description()


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

        self.input_text.configure(state="normal")
        self.input_text.delete("1.0", tk.END)
        self.input_text.edit_reset()
        self.input_text.tag_remove("error", "1.0", tk.END)
        self._soft_wrap_boundaries = set()
        self._wraps_captured = False

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

        self.stats_summary_var.set(
            "Time: 0.0 s  |  WPM: 0.0  |  Errors: 0  |  Error %: 0.0"
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
        if self._active_tab_key == "helper" and (self.is_letter_mode or self.last_session_mode == "letter"):
            self.start_letter_mode()
            return

        if self._active_tab_key == "helper" and (self.is_special_mode or self.last_session_mode == "special"):
            self.start_special_mode()
            return

        if self._active_tab_key == "helper" and (self.is_number_mode or self.last_session_mode == "number"):
            self.start_number_mode()
            return

        self.reset_session()
        self._refresh_mode_description(update_status=True)


    def start_letter_mode(self) -> None:
        """
        Activate the single letter training mode with a new random sequence.
        """
        if not self._prepare_drill_characters("letter"):
            return
        self._choose_practice("helper")
        self._helper_kind = "letter"
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
        self.info_text_var.set(info_text)
        self._update_letter_display()
        self.update_letter_status_label()
        self.last_session_mode = "letter"
        self._refresh_mode_description()

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
        can_avoid_repeat = len({c.lower() for c in self._drill_characters}) > 1
        while len(self.letter_sequence) < target_length:
            candidate = random.choice(self._drill_characters)
            if can_avoid_repeat and previous_lower and candidate.lower() == previous_lower:
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
            self.info_text_var.set(progress)
        else:
            self.info_text_var.set(
                "Letter mode: No active letter. Click the button to start."
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

        self.stats_summary_var.set(
            f"Letter mode  |  Time: {elapsed_seconds:.1f} s  |  "
            f"Letters/min: {letters_per_minute:.1f}  |  "
            f"Progress: {progress}  |  "
            f"{error_text}"
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

        self.info_text_var.set(info_message)
        self.stats_summary_var.set(summary)

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
        if not self._prepare_drill_characters("special"):
            return
        self._choose_practice("helper")
        self._helper_kind = "special"
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
        self.info_text_var.set(info_text)
        self._update_special_display()
        self.update_special_status_label()
        self.last_session_mode = "special"
        self._refresh_mode_description()

    def _extend_special_sequence(self, chunk_size: int = SPECIAL_SEQUENCE_LENGTH) -> None:
        """
        Append additional random special characters without consecutive duplicates.
        """
        if chunk_size <= 0:
            return
        previous_char = self.special_sequence[-1] if self.special_sequence else ""
        target_length = len(self.special_sequence) + chunk_size
        while len(self.special_sequence) < target_length:
            candidate = random.choice(self._drill_characters)
            if len(self._drill_characters) > 1 and previous_char and candidate == previous_char:
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
            self.info_text_var.set(progress)
        else:
            self.info_text_var.set(
                "Special character mode: No active symbol. Click the button to start."
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

        self.stats_summary_var.set(
            f"Special char mode  |  Time: {elapsed_seconds:.1f} s  |  "
            f"Symbols/min: {symbols_per_minute:.1f}  |  "
            f"Progress: {progress}  |  "
            f"{error_text}"
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

        self.info_text_var.set(info_message)
        self.stats_summary_var.set(summary)

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
        if not self._prepare_drill_characters("number"):
            return
        self._choose_practice("helper")
        self._helper_kind = "number"
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
        self.info_text_var.set(info_text)
        self._update_number_display()
        self.update_number_status_label()
        self.last_session_mode = "number"
        self._refresh_mode_description()

    def _extend_number_sequence(self, chunk_size: int = NUMBER_SEQUENCE_LENGTH) -> None:
        """
        Append additional random digits while avoiding immediate repeats.
        """
        if chunk_size <= 0:
            return
        previous_digit = self.number_sequence[-1] if self.number_sequence else ""
        target_length = len(self.number_sequence) + chunk_size
        while len(self.number_sequence) < target_length:
            candidate = random.choice(self._drill_characters)
            if len(self._drill_characters) > 1 and previous_digit and candidate == previous_digit:
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
            self.info_text_var.set(progress)
        else:
            self.info_text_var.set(
                "Number mode: No active digit. Click the button to start."
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

        self.stats_summary_var.set(
            f"Number mode  |  Time: {elapsed_seconds:.1f} s  |  "
            f"Digits/min: {digits_per_minute:.1f}  |  "
            f"Progress: {progress}  |  "
            f"{error_text}"
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

        self.info_text_var.set(info_message)
        self.stats_summary_var.set(summary)

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
        if self.finished:
            return

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
            self.info_text_var.set(
                "Please select and load a text before typing."
            )
            return

        if self.finished:
            return

        if self.start_time is None:
            if len(event.char) == 0:
                return
            self._capture_soft_wraps()
            self.start_time = time.time()
            self.schedule_periodic_update()

        self.update_typing_state()


    def _capture_soft_wraps(self) -> None:
        """Freeze the target's actual visual wrap points at the start of a run."""
        if self._wraps_captured:
            return
        self.master.update_idletasks()
        widget = self.display_text_widgets["typing"]
        boundaries = set()
        start = "1.0"
        while widget.compare(start, "<", "end-1c"):
            following = widget.index(f"{start} +1 display lines display linestart")
            if widget.compare(following, "<=", start):
                break
            offset = len(widget.get("1.0", following))
            if 0 < offset < len(self.target_text) and self.target_text[offset - 1] != "\n":
                boundaries.add(offset)
            start = following
        self._soft_wrap_boundaries = boundaries
        self._wraps_captured = True

    def _read_typing_input(self) -> tuple[str, list[int]]:
        raw = self.input_text.get("1.0", "end-1c")
        return normalize_wrapped_input(self.target_text, raw, self._soft_wrap_boundaries)

    def _on_typing_input_changed(self, event: tk.Event) -> None:
        widget = event.widget
        if not widget.edit_modified():
            return
        widget.edit_modified(False)
        if (widget is not self.input_text or self._active_tab_key != "typing"
                or self.is_letter_mode or self.is_special_mode or self.is_number_mode
                or not self.target_text or self.finished):
            return
        if self.start_time is None:
            if not widget.get("1.0", "end-1c"):
                return
            self._capture_soft_wraps()
            self.start_time = time.time()
            self.schedule_periodic_update()
        else:
            self.update_typing_state()


    def schedule_periodic_update(self) -> None:
        """
        Schedule periodic updates of WPM and error highlighting.
        """
        if self.finished:
            return

        self.update_typing_state()
        if self.finished:
            return
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

        typed_text, raw_offsets = self._read_typing_input()
        if self.is_blind_mode_active():
            self._update_blind_target_indicator(len(typed_text))

        # First update cumulative error counter based on the change.
        self._update_error_counter(self.previous_text, typed_text)

        # Then update current error highlighting and correct-count.
        first_error_index = self.highlight_errors(typed_text, raw_offsets)

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


    def highlight_errors(self, typed_text: str, raw_offsets: list[int] | None = None) -> int | None:
        """
        Highlight incorrect characters in the input text.

        A character is considered incorrect if it does not match the target
        text at the same position. Additional characters beyond the length of
        the target are also considered incorrect. This function also updates
        the current number of correct characters.
        """
        self.input_text.tag_remove("error", "1.0", tk.END)
        show_error_tags = not self.is_blind_mode_active() or self.blind_reveal_active

        if raw_offsets is None:
            raw_offsets = list(range(len(typed_text)))

        correct = 0
        first_error_index: int | None = None

        for index, char in enumerate(typed_text):
            if index >= len(self.target_text):
                if show_error_tags:
                    start = f"1.0 + {raw_offsets[index]} chars"
                    end = f"1.0 + {raw_offsets[index] + 1} chars"
                    self.input_text.tag_add("error", start, end)
                if first_error_index is None:
                    first_error_index = index
                continue

            if char != self.target_text[index]:
                if show_error_tags:
                    start = f"1.0 + {raw_offsets[index]} chars"
                    end = f"1.0 + {raw_offsets[index] + 1} chars"
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
        self.input_text.configure(state="disabled")

        if self.update_job_id is not None:
            self.master.after_cancel(self.update_job_id)
            self.update_job_id = None

        typed_text = self._read_typing_input()[0]
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

        self.info_text_var.set(
            f"Sudden death failed after {safe_index} characters. "
            "Load a text to try again."
        )
        self.stats_summary_var.set(
            f"Sudden death  |  Time: {elapsed_seconds:.1f} s  |  "
            f"Correct chars: {safe_index}  |  WPM: {wpm:.1f}"
            + (
                f"  |  End error %: {blind_end_error_percentage:.1f}"
                if blind_end_error_percentage is not None
                else ""
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
            self.stats_summary_var.set(text)
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

        self.stats_summary_var.set(
            f"Time: {elapsed_seconds:.1f} s  |  "
            f"WPM: {wpm:.1f}  |  "
            + (
                "Errors: hidden  |  Error %: hidden"
                if self.is_blind_mode_active()
                else f"Errors: {errors}  |  Error %: {error_percentage:.1f}"
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
        self.input_text.configure(state="disabled")

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
            self.info_text_var.set(
                "Sudden death complete. Start another run when ready."
            )
            self.stats_summary_var.set(
                f"Sudden death  |  Time: {elapsed_seconds:.1f} s  |  "
                f"WPM: {wpm:.1f}  |  Correct chars: {target_length}"
                + (
                    f"  |  End error %: {end_error_percentage:.1f}"
                    if end_error_percentage is not None
                    else ""
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
            self.stats_summary_var.set(summary)


    def show_result(self) -> None:
        """
        Show a simple dialog with statistics for the current session.

        If there is no valid timing or no text has been typed, a message is
        displayed informing the user.
        """
        typed_text = self._read_typing_input()[0].strip()
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
