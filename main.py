"""Entry point for the typing trainer application."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from utils.io_utils import DataError, TEXT_FILE_NAME, get__file_path, load_or_create_texts
from utils.ui_utils import TypingTrainerApp


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        texts = load_or_create_texts(get__file_path(TEXT_FILE_NAME))
        TypingTrainerApp(root, texts)
    except (DataError, OSError) as error:
        messagebox.showerror("Cannot open Typing Trainer", str(error), parent=root)
        root.destroy()
        return

    def report_error(exception, value, traceback):
        if isinstance(value, (DataError, OSError)):
            messagebox.showerror("Could not access user data", str(value), parent=root)
        else:
            root.__class__.report_callback_exception(root, exception, value, traceback)

    root.report_callback_exception = report_error
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
