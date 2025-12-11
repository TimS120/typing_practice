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
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox


TEXT_FILE_NAME = "typing_texts.txt"
STATS_FILE_NAME = "typing_stats.csv"
DEFAULT_FONT_FAMILY = "Courier New"
DEFAULT_FONT_SIZE = 12
MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 48


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

        self.current_font_size: int = DEFAULT_FONT_SIZE
        self.text_font: tkfont.Font | None = None

        self.error_count: int = 0
        self.correct_count: int = 0
        self.previous_text: str = ""

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
            text="A-",
            width=3,
            command=self.decrease_font_size
        )
        font_smaller_button.grid(row=0, column=1, padx=(5, 2), sticky="e")

        font_reset_button = ttk.Button(
            top_right_frame,
            text="A0",
            width=3,
            command=self.reset_font_size
        )
        font_reset_button.grid(row=0, column=2, padx=2, sticky="e")

        font_bigger_button = ttk.Button(
            top_right_frame,
            text="A+",
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
        control_frame.columnconfigure(0, weight=0)
        control_frame.columnconfigure(1, weight=0)
        control_frame.columnconfigure(2, weight=0)
        control_frame.columnconfigure(3, weight=1)

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

        # Initialize shared font for both text widgets
        self.text_font = tkfont.Font(
            family=DEFAULT_FONT_FAMILY,
            size=self.current_font_size
        )
        self.display_text.configure(font=self.text_font)
        self.input_text.configure(font=self.text_font)


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
        self.error_count = 0
        self.correct_count = 0
        self.previous_text = ""

        self.wpm_label.configure(
            text="Time: 0.0 s  |  WPM: 0.0  |  Errors: 0  |  Error %: 0.0"
        )

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

        with self.stats_file_path.open("r", encoding="utf-8") as stats_file:
            for line in stats_file:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) < 2:
                    continue

                try:
                    wpm_val = float(parts[1])
                except ValueError:
                    continue
                wpm_values.append(wpm_val)

                if len(parts) >= 3:
                    try:
                        err_val = float(parts[2])
                    except ValueError:
                        err_val = None
                    if err_val is not None:
                        error_rates.append(err_val)
                        wpm_for_3d.append(wpm_val)
                        error_for_3d.append(err_val)

        if not wpm_values:
            messagebox.showinfo(
                "Statistics",
                "No valid WPM data available in the statistics file.",
            )
            return

        # Create a 2x2 layout where the bottom axis spans both columns for the 3D plot
        fig = plt.figure(figsize=(10, 8))
        grid_spec = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.2])

        ax_wpm = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_3d = fig.add_subplot(grid_spec[1, :], projection="3d")

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
