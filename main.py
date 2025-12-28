"""
Entry point for the typing trainer application.
"""

from __future__ import annotations

import tkinter as tk

from utils.io_utils import TEXT_FILE_NAME, get__file_path, load_or_create_texts
from utils.ui_utils import TypingTrainerApp


def main() -> None:
    """
    Initialize data, create the Tk application, and start the main loop.
    """
    text_file_path = get__file_path(TEXT_FILE_NAME)
    texts = load_or_create_texts(text_file_path)

    root = tk.Tk()
    TypingTrainerApp(root, texts)
    root.mainloop()


if __name__ == "__main__":
    main()
