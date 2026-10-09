"""
Utility helpers for accessing and maintaining typing trainer data files.
"""

from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import io
import json
import os
import re
import tempfile

from cryptography.fernet import Fernet, InvalidToken

TEXT_FILE_NAME = "texts.json"
TEXT_LANGUAGES = ("English", "German")
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


class DataError(ValueError):
    """Stored user data could not be read safely."""


def get_data_dir() -> Path:
    """Keep user data beside the application in the Git-ignored data folder."""
    directory = Path(__file__).resolve().parents[1] / "data"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory


def get__file_path(file_path: str) -> Path:
    return get_data_dir() / (file_path + ".enc")


def _atomic_write(path: Path, data: bytes) -> None:
    """Replace a file atomically, without plaintext temporary data."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _cipher(directory: Path) -> Fernet:
    key_path = directory / "storage.key"
    if not key_path.exists():
        if any(directory.glob("*.enc")):
            raise DataError("The encryption key is missing. Restore storage.key with your data backup.")
        try:
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as stream:
                stream.write(Fernet.generate_key())
    try:
        return Fernet(key_path.read_bytes())
    except ValueError as error:
        raise DataError("The local encryption key is invalid.") from error


def read_encrypted(path: Path) -> str:
    cipher = _cipher(path.parent)
    try:
        payload = json.loads(cipher.decrypt(path.read_bytes()))
        if payload["file"] != path.name or not isinstance(payload["content"], str):
            raise ValueError("Invalid payload")
        return payload["content"]
    except (InvalidToken, ValueError, KeyError, TypeError) as error:
        raise DataError(f"Cannot read {path.name}: data or its encryption key was modified.") from error


def write_encrypted(path: Path, content: str) -> None:
    payload = json.dumps({"file": path.name, "content": content}, ensure_ascii=False).encode("utf-8")
    _atomic_write(path, _cipher(path.parent).encrypt(payload))


@contextmanager
def open_encrypted_stats(path: Path, mode: str = "r"):
    """Expose CSV only in memory; all statistics on disk stay authenticated/encrypted."""
    content = read_encrypted(path) if path.exists() else ""
    if mode == "r" and not path.exists():
        raise FileNotFoundError(path)
    stream = io.StringIO(content)
    if mode == "a":
        stream.seek(0, io.SEEK_END)
    try:
        yield stream
        if mode == "a":
            write_encrypted(path, stream.getvalue())
    finally:
        stream.close()


def validate_texts(entries: list[dict[str, str]], require_language: bool = True) -> None:
    if not isinstance(entries, list):
        raise ValueError("The text library must be a list.")
    for entry in entries:
        if (not isinstance(entry, dict) or set(entry) not in ({"name", "text"}, {"name", "text", "language"})
                or not isinstance(entry["name"], str) or not entry["name"].strip()
                or not isinstance(entry["text"], str) or not entry["text"]):
            raise ValueError("Every text needs a name and non-empty content.")
        if "language" in entry and not isinstance(entry["language"], str):
            raise ValueError("Text language must be a string.")
        if require_language and entry.get("language", "").strip() in ("", "-"):
            raise ValueError(f"Language required for ‘{entry['name']}’. Set each text's language before saving.")
        if require_language and entry["language"] not in TEXT_LANGUAGES:
            raise ValueError("Text language must be English or German.")


def load_or_create_texts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        save_texts(path, [])
        return []
    try:
        entries = json.loads(read_encrypted(path))
        validate_texts(entries, require_language=False)
        return [dict(entry, language=entry.get("language", "")) for entry in entries]
    except DataError:
        raise
    except (ValueError, TypeError) as error:
        raise DataError("Cannot read the text library. Restore a valid backup.") from error


def save_texts(path: Path, entries: list[dict[str, str]]) -> None:
    validate_texts(entries)
    write_encrypted(path, json.dumps(entries, ensure_ascii=False))


def ensure_stats_file_header(path: Path, header: str, create_if_missing: bool = True) -> None:
    if not path.exists():
        if create_if_missing:
            write_encrypted(path, header + "\n")
        return
    content = read_encrypted(path)
    if content.splitlines()[:1] != [header]:
        write_encrypted(path, header + "\n" + content)


def load_settings() -> dict:
    path = get_data_dir() / "settings.json"
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(settings, dict):
        return {}
    result = {}
    if settings.get("theme") in ("system", "light", "dark"):
        result["theme"] = settings["theme"]
    size = settings.get("font_size")
    if type(size) is int and 6 <= size <= 48:
        result["font_size"] = size
    ui_size = settings.get("ui_font_size")
    if type(ui_size) is int and 8 <= ui_size <= 24:
        result["ui_font_size"] = ui_size
    dimensions = settings.get("window_size")
    if isinstance(dimensions, str) and re.fullmatch(r"[1-9]\d{0,4}x[1-9]\d{0,4}", dimensions):
        result["window_size"] = dimensions
    language = settings.get("generation_language")
    if language in TEXT_LANGUAGES:
        result["generation_language"] = language
    from .mistake_analysis import HISTORY_RANGES
    history = settings.get("analysis_history")
    if history in HISTORY_RANGES:
        result["analysis_history"] = history
    minimum = settings.get("analysis_minimum")
    if type(minimum) is int and minimum >= 1:
        result["analysis_minimum"] = minimum
    from .keyboard_layouts import LAYOUTS
    layout = settings.get("keyboard_layout")
    if layout in (*LAYOUTS, "Custom"):
        result["keyboard_layout"] = layout
    custom = settings.get("custom_characters")
    if isinstance(custom, str) and custom:
        result["custom_characters"] = custom
    threshold = settings.get("coverage_threshold")
    if type(threshold) is int and threshold >= 0:
        result["coverage_threshold"] = threshold
    if result.get("keyboard_layout") == "Custom" and not result.get("custom_characters"):
        result.pop("keyboard_layout")
    return result


def save_settings(settings: dict) -> None:
    _atomic_write(get_data_dir() / "settings.json", json.dumps(settings, indent=2).encode("utf-8"))
