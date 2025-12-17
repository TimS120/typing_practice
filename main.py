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
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox


TEXT_FILE_NAME = "typing_texts.txt"
STATS_FILE_NAME = "typing_stats.csv"
LETTER_STATS_FILE_NAME = "letter_stats.csv"
NUMBER_STATS_FILE_NAME = "number_stats.csv"
DEFAULT_FONT_FAMILY = "Courier New"
DEFAULT_FONT_SIZE = 12
MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 48
LETTER_SEQUENCE_LENGTH = 100
NUMBER_SEQUENCE_LENGTH = 100


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
        self.number_stats_file_path: Path = get__file_path(NUMBER_STATS_FILE_NAME)

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
        self.is_number_mode: bool = False
        self.number_sequence: List[str] = []
        self.number_index: int = 0
        self.number_total_digits: int = 0
        self.number_errors: int = 0
        self.number_correct_digits: int = 0

        self._build_gui()


    def _build_gui(self) -> None:
        """
        Create all GUI widgets.
        """
        self.master.title("Typing Trainer")

        self.master.geometry("900x550")

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

        for idx, text in enumerate(self.texts):
            first_line = text.splitlines()[0] if text.splitlines() else text
            preview = (
                first_line if len(first_line) <= 40 else first_line[:37] + "..."
            )
            self.text_listbox.insert(tk.END, f"{idx + 1:02d}  {preview}")

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

        self.wpm_label = ttk.Label(
            right_frame,
            text="Time: 0.0 s  |  WPM: 0.0  |  Errors: 0  |  Error %: 0.0"
        )
        self.wpm_label.grid(row=1, column=0, sticky="e")

        self.display_text = tk.Text(
            right_frame,
            height=6,
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
        for idx in range(7):
            control_frame.columnconfigure(idx, weight=0)
        control_frame.columnconfigure(7, weight=1)

        reset_button = ttk.Button(
            control_frame,
            text="Reset session",
            command=self.reset_session
        )
        reset_button.grid(row=0, column=0, padx=(0, 5))

        show_stats_button = ttk.Button(
            control_frame,
            text="Show result",
            command=self.show_result
        )
        show_stats_button.grid(row=0, column=1, padx=(5, 5))

        histogram_button = ttk.Button(
            control_frame,
            text="Show stats",
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

        number_mode_button = ttk.Button(
            control_frame,
            text="Number mode",
            command=self.start_number_mode
        )
        number_mode_button.grid(row=0, column=5, padx=(5, 0))

        number_stats_button = ttk.Button(
            control_frame,
            text="Number stats",
            command=self.show_number_stats
        )
        number_stats_button.grid(row=0, column=6, padx=(5, 0))

        # Initialize shared font for both text widgets
        self.text_font = tkfont.Font(
            family=DEFAULT_FONT_FAMILY,
            size=self.current_font_size
        )
        self.display_text.configure(font=self.text_font)
        self.input_text.configure(font=self.text_font)


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
        self.selected_text = self.texts[index]
        self._apply_loaded_text()


    def on_load_random(self) -> None:
        """
        Load a random text from the list of available texts.
        """
        index = random.randrange(len(self.texts))
        self.text_listbox.selection_clear(0, tk.END)
        self.text_listbox.selection_set(index)
        self.selected_text = self.texts[index]
        self._apply_loaded_text()


    def _apply_loaded_text(self) -> None:
        """
        Display the selected text and reset the typing session.
        """
        normalized_lines = [
            line.rstrip()
            for line in self.selected_text.splitlines()
        ]
        self.target_text = "\n".join(normalized_lines)

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
        exit_number_mode: bool = True
    ) -> None:
        """
        Reset timing and input state for a new typing session.

        :param clear_display: Whether the target text display should be cleared
        :param exit_letter_mode: Whether letter mode should be deactivated
        :param exit_number_mode: Whether number mode should be deactivated
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
        self.letter_errors = 0
        self.letter_correct_letters = 0
        self.letter_previous_text = ""
        self.number_errors = 0
        self.number_correct_digits = 0

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

        self.wpm_label.configure(
            text="Time: 0.0 s  |  WPM: 0.0  |  Errors: 0  |  Error %: 0.0"
        )

        if self.update_job_id is not None:
            self.master.after_cancel(self.update_job_id)
            self.update_job_id = None


    def start_letter_mode(self) -> None:
        """
        Activate the single letter training mode with a new random sequence.
        """
        self.reset_session(clear_display=True)
        self.is_letter_mode = True
        self.letter_sequence = []
        previous_lower = ""
        while len(self.letter_sequence) < LETTER_SEQUENCE_LENGTH:
            candidate = random.choice(string.ascii_letters)
            if previous_lower and candidate.lower() == previous_lower:
                continue
            self.letter_sequence.append(candidate)
            previous_lower = candidate.lower()
        self.letter_index = 0
        self.letter_total_letters = len(self.letter_sequence)
        self.letter_errors = 0
        self.letter_correct_letters = 0
        self.start_time = None
        self.info_label.configure(
            text="Letter mode: random letters (upper/lower). Progress 0/100."
        )
        self._update_letter_display()
        self.update_letter_status_label()


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
                self.finish_letter_mode_session()
            else:
                self._update_letter_display()
                self.update_letter_status_label()
            return

        self.letter_errors += 1
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

        progress = f"{self.letter_correct_letters}/{self.letter_total_letters}"

        self.wpm_label.configure(
            text=(
                f"Letter mode  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Letters/min: {letters_per_minute:.1f}  |  "
                f"Progress: {progress}  |  "
                f"Errors: {self.letter_errors}"
            )
        )


    def finish_letter_mode_session(self) -> None:
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

        total_letters = max(self.letter_total_letters, 1)
        error_percentage = (self.letter_errors / total_letters) * 100.0

        self.save_letter_result(letters_per_minute, error_percentage)

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        self.display_text.insert(
            "1.0",
            "Letter mode finished. Click 'Letter mode' to start again."
        )
        self.display_text.configure(state="disabled")

        self.info_label.configure(
            text="Letter mode finished. Start a new run via the Letter mode button."
        )

        self.wpm_label.configure(
            text=(
                f"Letter mode complete  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Letters/min: {letters_per_minute:.1f}  |  "
                f"Errors: {self.letter_errors}  |  "
                f"Error %: {error_percentage:.1f}"
            )
        )

        self.input_text.delete("1.0", tk.END)
        self.is_letter_mode = False
        self.start_time = None
        self.letter_sequence = []
        self.letter_index = 0
        self.letter_total_letters = 0
        self.letter_errors = 0
        self.letter_correct_letters = 0


    def start_number_mode(self) -> None:
        """
        Activate the numeric keypad training mode with a random digit sequence.
        """
        self.reset_session(clear_display=True)
        self.is_number_mode = True
        self.number_sequence = []
        previous_digit = ""
        while len(self.number_sequence) < NUMBER_SEQUENCE_LENGTH:
            candidate = random.choice(string.digits)
            if previous_digit and candidate == previous_digit:
                continue
            self.number_sequence.append(candidate)
            previous_digit = candidate
        self.number_index = 0
        self.number_total_digits = len(self.number_sequence)
        self.number_errors = 0
        self.number_correct_digits = 0
        self.start_time = None
        self.info_label.configure(
            text="Number mode: type digits with the numeric keypad. Progress 0/100."
        )
        self._update_number_display()
        self.update_number_status_label()


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
                self.finish_number_mode_session()
            else:
                self._update_number_display()
                self.update_number_status_label()
            return

        self.number_errors += 1
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

        progress = f"{self.number_correct_digits}/{self.number_total_digits}"

        self.wpm_label.configure(
            text=(
                f"Number mode  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Digits/min: {digits_per_minute:.1f}  |  "
                f"Progress: {progress}  |  "
                f"Errors: {self.number_errors}"
            )
        )


    def finish_number_mode_session(self) -> None:
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

        total_digits = max(self.number_total_digits, 1)
        error_percentage = (self.number_errors / total_digits) * 100.0

        self.save_number_result(digits_per_minute, error_percentage)

        self.display_text.configure(state="normal")
        self.display_text.delete("1.0", tk.END)
        self.display_text.insert(
            "1.0",
            "Number mode finished. Click 'Number mode' to start again."
        )
        self.display_text.configure(state="disabled")

        self.info_label.configure(
            text="Number mode finished. Start a new run via the Number mode button."
        )

        self.wpm_label.configure(
            text=(
                f"Number mode complete  |  Time: {elapsed_seconds:.1f} s  |  "
                f"Digits/min: {digits_per_minute:.1f}  |  "
                f"Errors: {self.number_errors}  |  "
                f"Error %: {error_percentage:.1f}"
            )
        )

        self.input_text.delete("1.0", tk.END)
        self.is_number_mode = False
        self.start_time = None
        self.number_sequence = []
        self.number_index = 0
        self.number_total_digits = 0
        self.number_errors = 0
        self.number_correct_digits = 0


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
        self.highlight_errors(typed_text)

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
        # Only differences from previous -> current are considered.
        max_len = len(current)
        for index in range(max_len):
            new_char = current[index]
            old_char = previous[index] if index < len(previous) else None

            # Only consider positions where something changed or was inserted.
            if old_char is not None and old_char == new_char:
                continue

            # New or changed char: check if it is wrong.
            if index >= len(self.target_text):
                # Beyond end of target: always an error.
                self.error_count += 1
            else:
                if new_char != self.target_text[index]:
                    self.error_count += 1


    def highlight_errors(self, typed_text: str) -> None:
        """
        Highlight incorrect characters in the input text.

        A character is considered incorrect if it does not match the target
        text at the same position. Additional characters beyond the length of
        the target are also considered incorrect. This function also updates
        the current number of correct characters.
        """
        self.input_text.tag_remove("error", "1.0", tk.END)

        correct = 0

        for index, char in enumerate(typed_text):
            if index >= len(self.target_text):
                start = f"1.0 + {index} chars"
                end = f"1.0 + {index + 1} chars"
                self.input_text.tag_add("error", start, end)
                continue

            if char != self.target_text[index]:
                start = f"1.0 + {index} chars"
                end = f"1.0 + {index + 1} chars"
                self.input_text.tag_add("error", start, end)
            else:
                correct += 1

        self.correct_count = correct


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

        self.save_wpm_result(wpm, error_percentage)


    def save_wpm_result(self, wpm: float, error_percentage: float) -> None:
        """
        Append the given WPM value and error rate to the statistics file.

        The values are appended as a simple CSV with three columns:
        timestamp;WPM;error_rate.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"{timestamp};{wpm:.3f};{error_percentage:.3f}\n"
        self.stats_file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.stats_file_path.open("a", encoding="utf-8") as stats_file:
            stats_file.write(line)


    def save_letter_result(
        self,
        letters_per_minute: float,
        error_percentage: float
    ) -> None:
        """
        Append the letter mode statistics to the dedicated CSV file.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = (
            f"{timestamp};{letters_per_minute:.3f};{error_percentage:.3f}\n"
        )
        self.letter_stats_file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.letter_stats_file_path.open("a", encoding="utf-8") as file:
            file.write(line)


    def save_number_result(
        self,
        digits_per_minute: float,
        error_percentage: float
    ) -> None:
        """
        Append the number mode statistics to the dedicated CSV file.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"{timestamp};{digits_per_minute:.3f};{error_percentage:.3f}\n"
        self.number_stats_file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.number_stats_file_path.open("a", encoding="utf-8") as file:
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


    def show_stats(self) -> None:
        """
        Show histograms of WPM, error percentage, and a 3D joint histogram
        in a single Matplotlib figure.

        If no statistics file exists or no valid values can be read, an
        information dialog is shown instead.
        """
        if not self.stats_file_path.exists():
            messagebox.showinfo(
                "Statistics",
                "No statistics file found yet. "
                "Finish at least one session."
            )
            return

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

                if day is not None:
                    entry = daily_stats.setdefault(
                        day,
                        {
                            "wpm_sum": 0.0,
                            "wpm_count": 0,
                            "error_sum": 0.0,
                            "error_count": 0
                        }
                    )
                    entry["wpm_sum"] += wpm_val
                    entry["wpm_count"] += 1
                    if err_val is not None:
                        entry["error_sum"] += err_val
                        entry["error_count"] += 1

        if not wpm_values:
            messagebox.showinfo(
                "Statistics",
                "No valid WPM data available in the statistics file.",
            )
            return

        daily_dates: List[date] = []
        daily_wpm: List[float] = []
        daily_error: List[float] = []
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
                else:
                    daily_wpm.append(0.0)
                    daily_error.append(0.0)
                current_day += timedelta(days=1)

        # Create a 3-row layout with the 3D and timeline plots spanning both columns
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.2, 1.0])

        ax_wpm = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_3d = fig.add_subplot(grid_spec[1, :], projection="3d")
        ax_time = fig.add_subplot(grid_spec[2, :])

        # 1D histogram of WPM
        ax_wpm.hist(wpm_values, bins="auto")
        ax_wpm.set_title("WPM distribution")
        ax_wpm.set_xlabel("Words per minute")
        ax_wpm.set_ylabel("Frequency")

        # 1D histogram of error percentage
        if error_rates:
            ax_error.hist(error_rates, bins="auto")
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
                transform=ax_error.transAxes
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        # 3D joint histogram of WPM vs error percentage
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
                    shade=True
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
                    va="center"
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
                va="center"
            )
            ax_3d.set_xticks([])
            ax_3d.set_yticks([])
            ax_3d.set_zticks([])

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.4
            ax_time.bar(
                positions - bar_width / 2.0,
                daily_wpm,
                width=bar_width,
                color="#7ec8f8",
                label="Average WPM"
            )
            ax_time.bar(
                positions + bar_width / 2.0,
                daily_error,
                width=bar_width,
                color="#f7c59f",
                label="Average error %"
            )
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                [day.strftime("%Y-%m-%d") for day in daily_dates],
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily average")
            ax_time.set_title("Daily averages (WPM vs error %)")
            ax_time.legend()
        else:
            ax_time.set_title("Daily averages (WPM vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])

        plt.tight_layout()
        plt.show()


    def show_letter_stats(self) -> None:
        """
        Visualize stored letter mode statistics (letters per minute and errors).
        """
        if not self.letter_stats_file_path.exists():
            messagebox.showinfo(
                "Letter statistics",
                "No letter statistics available yet. "
                "Finish at least one letter mode session."
            )
            return

        letters_per_minute: List[float] = []
        error_rates: List[float] = []
        daily_stats: dict = {}

        with self.letter_stats_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 3:
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
                letters_per_minute.append(lpm_val)
                error_rates.append(err_val)
                entry = daily_stats.setdefault(
                    day,
                    {
                        "speed_sum": 0.0,
                        "speed_count": 0,
                        "error_sum": 0.0,
                        "error_count": 0
                    }
                )
                entry["speed_sum"] += lpm_val
                entry["speed_count"] += 1
                entry["error_sum"] += err_val
                entry["error_count"] += 1

        if not letters_per_minute:
            messagebox.showinfo(
                "Letter statistics",
                "No valid data inside the letter statistics file."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_error: List[float] = []
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
                else:
                    daily_speed.append(0.0)
                    daily_error.append(0.0)
                current_day += timedelta(days=1)

        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.2, 1.0])

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_3d = fig.add_subplot(grid_spec[1, :], projection="3d")
        ax_time = fig.add_subplot(grid_spec[2, :])

        ax_speed.hist(letters_per_minute, bins="auto")
        ax_speed.set_title("Letters per minute distribution")
        ax_speed.set_xlabel("Letters per minute")
        ax_speed.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(error_rates, bins="auto")
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
                transform=ax_error.transAxes
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
                    shade=True
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
                    va="center"
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
                va="center"
            )
            ax_3d.set_xticks([])
            ax_3d.set_yticks([])
            ax_3d.set_zticks([])

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.4
            ax_time.bar(
                positions - bar_width / 2.0,
                daily_speed,
                width=bar_width,
                color="#7ec8f8",
                label="Average letters/min"
            )
            ax_time.bar(
                positions + bar_width / 2.0,
                daily_error,
                width=bar_width,
                color="#f7c59f",
                label="Average error %"
            )
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                [day.strftime("%Y-%m-%d") for day in daily_dates],
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily average")
            ax_time.set_title("Daily averages (letters/min vs error %)")
            ax_time.legend()
        else:
            ax_time.set_title("Daily averages (letters/min vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])

        plt.tight_layout()
        plt.show()


    def show_number_stats(self) -> None:
        """
        Visualize stored number mode statistics (digits per minute and errors).
        """
        if not self.number_stats_file_path.exists():
            messagebox.showinfo(
                "Number statistics",
                "No number statistics available yet. "
                "Finish at least one number mode session."
            )
            return

        digits_per_minute: List[float] = []
        error_rates: List[float] = []
        daily_stats: dict = {}

        with self.number_stats_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 3:
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
                digits_per_minute.append(dpm_val)
                error_rates.append(err_val)
                entry = daily_stats.setdefault(
                    day,
                    {
                        "speed_sum": 0.0,
                        "speed_count": 0,
                        "error_sum": 0.0,
                        "error_count": 0
                    }
                )
                entry["speed_sum"] += dpm_val
                entry["speed_count"] += 1
                entry["error_sum"] += err_val
                entry["error_count"] += 1

        if not digits_per_minute:
            messagebox.showinfo(
                "Number statistics",
                "No valid data inside the number statistics file."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_error: List[float] = []
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
                else:
                    daily_speed.append(0.0)
                    daily_error.append(0.0)
                current_day += timedelta(days=1)

        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.2, 1.0])

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_3d = fig.add_subplot(grid_spec[1, :], projection="3d")
        ax_time = fig.add_subplot(grid_spec[2, :])

        ax_speed.hist(digits_per_minute, bins="auto")
        ax_speed.set_title("Digits per minute distribution")
        ax_speed.set_xlabel("Digits per minute")
        ax_speed.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(error_rates, bins="auto")
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
                transform=ax_error.transAxes
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
                    shade=True
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
                    va="center"
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
                va="center"
            )
            ax_3d.set_xticks([])
            ax_3d.set_yticks([])
            ax_3d.set_zticks([])

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.4
            ax_time.bar(
                positions - bar_width / 2.0,
                daily_speed,
                width=bar_width,
                color="#7ec8f8",
                label="Average digits/min"
            )
            ax_time.bar(
                positions + bar_width / 2.0,
                daily_error,
                width=bar_width,
                color="#f7c59f",
                label="Average error %"
            )
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                [day.strftime("%Y-%m-%d") for day in daily_dates],
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily average")
            ax_time.set_title("Daily averages (digits/min vs error %)")
            ax_time.legend()
        else:
            ax_time.set_title("Daily averages (digits/min vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])

        plt.tight_layout()
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
