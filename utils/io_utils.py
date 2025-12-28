"""
Utility helpers for accessing and maintaining typing trainer data files.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

DATA_DIR_NAME = "data"

TEXT_FILE_NAME = "typing_texts.txt"
STATS_FILE_NAME = "typing_stats.csv"
LETTER_STATS_FILE_NAME = "letter_stats.csv"
SPECIAL_STATS_FILE_NAME = "special_character_stats.csv"
NUMBER_STATS_FILE_NAME = "number_stats.csv"
TRAINING_FLAG_COLUMN = "is_training_run"
END_ERROR_PERCENTAGE_COLUMN = "end_error_percentage"
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
BLIND_TYPING_STATS_FILE_NAME = "blind_typing_stats.csv"
BLIND_LETTER_STATS_FILE_NAME = "blind_letter_stats.csv"
BLIND_SPECIAL_STATS_FILE_NAME = "blind_special_stats.csv"
BLIND_NUMBER_STATS_FILE_NAME = "blind_number_stats.csv"
BLIND_TYPING_STATS_FILE_HEADER = (
    "timestamp;wpm;typed_characters;duration_seconds;completed;"
    f"{END_ERROR_PERCENTAGE_COLUMN};{TRAINING_FLAG_COLUMN}"
)
BLIND_LETTER_STATS_FILE_HEADER = (
    "timestamp;letters_per_minute;typed_letters;duration_seconds;completed;"
    f"{END_ERROR_PERCENTAGE_COLUMN};{TRAINING_FLAG_COLUMN}"
)
BLIND_SPECIAL_STATS_FILE_HEADER = (
    "timestamp;symbols_per_minute;typed_symbols;duration_seconds;completed;"
    f"{END_ERROR_PERCENTAGE_COLUMN};{TRAINING_FLAG_COLUMN}"
)
BLIND_NUMBER_STATS_FILE_HEADER = (
    "timestamp;digits_per_minute;typed_digits;duration_seconds;completed;"
    f"{END_ERROR_PERCENTAGE_COLUMN};{TRAINING_FLAG_COLUMN}"
)


def _get_project_root() -> Path:
    """
    Return the project root folder that contains the utils package.
    """
    try:
        return Path(__file__).resolve().parents[1]
    except NameError:
        return Path.cwd()


def get_data_dir() -> Path:
    """
    Return the folder that contains the data files, creating it if necessary.
    """
    data_dir = _get_project_root() / DATA_DIR_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get__file_path(file_path: str) -> Path:
    """
    Return a path to a file within the managed data directory.
    """
    return get_data_dir() / file_path


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
        "Robots can move precisely if their controllers are well designed."
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
    path.parent.mkdir(parents=True, exist_ok=True)
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
