"""
Typing trainer with live words per minute feedback.

This module provides a Tkinter based typing trainer. It loads a list of
training texts from a file, allows the user to select a text, and then measures
the words per minute (WPM) while the user types. Completed session WPM values
are stored in a statistics file and can be visualized.
"""

from __future__ import annotations

import time
from pathlib import Path
import random
from typing import List

import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, messagebox


TEXT_FILE_NAME = "typing_texts.txt"
STATS_FILE_NAME = "typing_stats.csv"


def get__file_path(file_path) -> Path:
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
        "well designed.",
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

        self._build_gui()

    def _build_gui(self) -> None:
        """
        Create all GUI widgets.
        """
        self.master.title("Typing Trainer")

        self.master.geometry("900x500")

        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.master, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10))

        ttk.Label(list_frame, text="Available texts").grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 5),
        )

        self.text_listbox = tk.Listbox(
            list_frame,
            height=20,
            width=30,
            exportselection=False,
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
            command=self.on_load_selected,
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

        self.wpm_label = ttk.Label(right_frame, text="WPM: 0.0")
        self.wpm_label.grid(row=0, column=0, sticky="e")

        self.info_label = ttk.Label(
            right_frame,
            text="Select a text on the left and click Load.",
        )
        self.info_label.grid(row=1, column=0, sticky="w", pady=(0, 5))

        self.display_text = tk.Text(
            right_frame,
            height=6,
            wrap="word",
            state="disabled",
        )
        self.display_text.grid(row=2, column=0, sticky="nsew")

        input_frame = ttk.LabelFrame(right_frame, text="Your input")
        input_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)

        self.input_text = tk.Text(
            input_frame,
            height=8,
            wrap="word",
        )
        self.input_text.grid(row=0, column=0, sticky="nsew")

        # Tag for highlighting incorrect characters.
        self.input_text = tk.Text(
            input_frame,
            height=8,
            wrap="word",
        )
        self.input_text.grid(row=0, column=0, sticky="nsew")

        # Tag for highlighting incorrect characters (also spaces).
        self.input_text.tag_configure(
            "error",
            foreground="red",
            background="#ffcccc",  # light red rectangle behind wrong chars, including spaces
        )

        self.input_text.bind("<Key>", self.on_key_press)
        self.input_text.bind("<Key>", self.on_key_press)

        control_frame = ttk.Frame(right_frame)
        control_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        control_frame.columnconfigure(0, weight=0)
        control_frame.columnconfigure(1, weight=0)
        control_frame.columnconfigure(2, weight=0)
        control_frame.columnconfigure(3, weight=1)

        reset_button = ttk.Button(
            control_frame,
            text="Reset session",
            command=self.reset_session,
        )
        reset_button.grid(row=0, column=0, padx=(0, 5))

        show_stats_button = ttk.Button(
            control_frame,
            text="Show result",
            command=self.show_result,
        )
        show_stats_button.grid(row=0, column=1, padx=(5, 5))

        histogram_button = ttk.Button(
            control_frame,
            text="Show WPM histogram",
            command=self.show_histogram,
        )
        histogram_button.grid(row=0, column=2, padx=(5, 0))

    def on_load_selected(self) -> None:
        """
        Load the text that is currently selected in the listbox.
        """
        selection = self.text_listbox.curselection()
        if not selection:
            messagebox.showinfo(
                "Selection",
                "Please select a text in the list.",
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
        normalized_lines = [line.rstrip() for line in self.selected_text.splitlines()]  # Removing of trailing spaces on each line
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

    def reset_session(self, clear_display: bool = False) -> None:
        """
        Reset timing and input state for a new typing session.

        :param clear_display: Whether the target text display should be cleared.
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
        self.wpm_label.configure(text="WPM: 0.0")

        if self.update_job_id is not None:
            self.master.after_cancel(self.update_job_id)
            self.update_job_id = None

    def on_key_press(self, event: tk.Event) -> None:
        """
        Handle key presses in the input box and start timing if needed.

        The function starts the timer on the first non control key and triggers
        updates of WPM and error highlighting. If the text is already finished,
        additional key presses do not change the statistics.
        """
        if self.target_text == "":
            self.info_label.configure(
                text="Please select and load a text before typing.",
            )
            return

        if self.finished:  # After finishing, WPM is frozen and further typing is ignored for statistics.
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
        self.highlight_errors(typed_text)
        self.update_wpm(typed_text)
        self.check_completion(typed_text)

    def highlight_errors(self, typed_text: str) -> None:
        """
        Highlight incorrect characters in the input text.

        A character is considered incorrect if it does not match the target
        text at the same position. Additional characters beyond the length of
        the target are also considered incorrect.
        """
        self.input_text.tag_remove("error", "1.0", tk.END)

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

    def update_wpm(self, typed_text: str) -> None:
        """
        Compute the current words per minute and update the label.

        :param typed_text: Text currently typed by the user.
        """
        if self.start_time is None:
            self.wpm_label.configure(text="WPM: 0.0")
            return

        words = len(typed_text.split())
        elapsed_seconds = max(time.time() - self.start_time, 0.0001)
        elapsed_minutes = elapsed_seconds / 60.0
        wpm = words / elapsed_minutes if elapsed_minutes > 0.0 else 0.0001

        self.wpm_label.configure(text=f"WPM: {wpm:.1f}")

    def check_completion(self, typed_text: str) -> None:
        """
        Check whether the user has fully and correctly typed the target text.

        Once the text is completed, the timer is stopped, the final WPM value
        is frozen, and the result is saved to the statistics file.
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

        self.wpm_label.configure(text=f"WPM: {wpm:.1f}")

        self.save_wpm_result(wpm)

    def save_wpm_result(self, wpm: float) -> None:
        """
        Append the given WPM value to the statistics file.

        The values are appended as a simple CSV with two columns:
        timestamp and WPM.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"{timestamp};{wpm:.3f}\n"
        self.stats_file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.stats_file_path.open("a", encoding="utf-8") as stats_file:
            stats_file.write(line)

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

    def show_histogram(self) -> None:
        """
        Show a histogram of all stored WPM results in a Matplotlib window.

        If no statistics file exists or no valid values can be read, an
        information dialog is shown instead.
        """
        if not self.stats_file_path.exists():
            messagebox.showinfo(
                "Statistics",
                "No statistics file found yet. "
                "Finish at least one session.",
            )
            return

        wpm_values: List[float] = []

        with self.stats_file_path.open("r", encoding="utf-8") as stats_file:
            for line in stats_file:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) < 2:
                    continue
                try:
                    value = float(parts[1])
                except ValueError:
                    continue
                wpm_values.append(value)

        if not wpm_values:
            messagebox.showinfo(
                "Statistics",
                "No valid WPM data available in the statistics file.",
            )
            return

        plt.figure()
        plt.hist(wpm_values, bins="auto")
        plt.title("WPM distribution")
        plt.xlabel("Words per minute")
        plt.ylabel("Frequency")
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
