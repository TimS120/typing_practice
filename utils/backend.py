"""
Backend helpers for the typing trainer application.
"""

from __future__ import annotations

import time
from pathlib import Path

from .io_utils import (
    BLIND_LETTER_STATS_FILE_HEADER,
    BLIND_SPECIAL_STATS_FILE_HEADER,
    BLIND_TYPING_STATS_FILE_HEADER,
    BLIND_NUMBER_STATS_FILE_HEADER,
    LETTER_STATS_FILE_HEADER,
    NUMBER_STATS_FILE_HEADER,
    SPECIAL_STATS_FILE_HEADER,
    STATS_FILE_HEADER,
    SUDDEN_DEATH_LETTER_STATS_FILE_HEADER,
    SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER,
    SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER,
    SUDDEN_DEATH_TYPING_STATS_FILE_HEADER,
    ensure_stats_file_header,
)


def parse_training_flag(parts: list[str], flag_index: int) -> bool:
    """
    Safely parse the training flag from a CSV row.
    """
    if len(parts) <= flag_index:
        return False
    value = parts[flag_index].strip().lower()
    return value in {"1", "true", "yes", "y"}


def calculate_end_error_percentage(
    target: str,
    typed: str,
    total_targets: int | None = None,
) -> float:
    """
    Compute the percentage of mismatched characters between target and typed text.
    """
    if total_targets is None:
        total_targets = len(typed)
    if total_targets <= 0:
        return 0.0
    wrong = 0
    for index in range(total_targets):
        target_char = target[index] if index < len(target) else ""
        typed_char = typed[index] if index < len(typed) else ""
        if typed_char != target_char:
            wrong += 1
    if len(typed) > total_targets:
        wrong += len(typed) - total_targets
    return (wrong / total_targets) * 100.0


def save_wpm_result(
    file_path: Path,
    wpm: float,
    error_percentage: float,
    duration_seconds: float,
    is_training_run: bool,
) -> None:
    """
    Append the given WPM value and error rate to the statistics file.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    training_flag = "1" if is_training_run else "0"
    line = (
        f"{timestamp};{wpm:.3f};{error_percentage:.3f};"
        f"{duration_seconds:.3f};{training_flag}\n"
    )
    ensure_stats_file_header(file_path, STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_sudden_death_wpm_result(
    file_path: Path,
    wpm: float,
    correct_characters: int,
    duration_seconds: float,
    completed: bool,
    is_training_run: bool,
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
    ensure_stats_file_header(file_path, SUDDEN_DEATH_TYPING_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_letter_result(
    file_path: Path,
    letters_per_minute: float,
    error_percentage: float,
    duration_seconds: float,
    is_training_run: bool,
) -> None:
    """
    Append the letter mode statistics to the dedicated CSV file.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    training_flag = "1" if is_training_run else "0"
    line = (
        f"{timestamp};{letters_per_minute:.3f};{error_percentage:.3f};"
        f"{duration_seconds:.3f};{training_flag}\n"
    )
    ensure_stats_file_header(file_path, LETTER_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_sudden_death_letter_result(
    file_path: Path,
    letters_per_minute: float,
    correct_letters: int,
    duration_seconds: float,
    completed: bool,
    is_training_run: bool,
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
    ensure_stats_file_header(file_path, SUDDEN_DEATH_LETTER_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_special_result(
    file_path: Path,
    symbols_per_minute: float,
    error_percentage: float,
    duration_seconds: float,
    is_training_run: bool,
) -> None:
    """
    Append the special character mode statistics to the dedicated CSV file.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    training_flag = "1" if is_training_run else "0"
    line = (
        f"{timestamp};{symbols_per_minute:.3f};{error_percentage:.3f};"
        f"{duration_seconds:.3f};{training_flag}\n"
    )
    ensure_stats_file_header(file_path, SPECIAL_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_sudden_death_special_result(
    file_path: Path,
    symbols_per_minute: float,
    correct_symbols: int,
    duration_seconds: float,
    completed: bool,
    is_training_run: bool,
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
    ensure_stats_file_header(file_path, SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_number_result(
    file_path: Path,
    digits_per_minute: float,
    error_percentage: float,
    duration_seconds: float,
    is_training_run: bool,
) -> None:
    """
    Append the number mode statistics to the dedicated CSV file.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    training_flag = "1" if is_training_run else "0"
    line = (
        f"{timestamp};{digits_per_minute:.3f};{error_percentage:.3f};"
        f"{duration_seconds:.3f};{training_flag}\n"
    )
    ensure_stats_file_header(file_path, NUMBER_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_sudden_death_number_result(
    file_path: Path,
    digits_per_minute: float,
    correct_digits: int,
    duration_seconds: float,
    completed: bool,
    is_training_run: bool,
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
    ensure_stats_file_header(file_path, SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_blind_typing_result(
    file_path: Path,
    wpm: float,
    typed_characters: int,
    duration_seconds: float,
    completed: bool,
    end_error_percentage: float,
    is_training_run: bool,
) -> None:
    """
    Store blind mode typing results with the final error percentage.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    completed_flag = "1" if completed else "0"
    training_flag = "1" if is_training_run else "0"
    line = (
        f"{timestamp};{wpm:.3f};{typed_characters};{duration_seconds:.3f};"
        f"{completed_flag};{end_error_percentage:.3f};{training_flag}\n"
    )
    ensure_stats_file_header(file_path, BLIND_TYPING_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_blind_letter_result(
    file_path: Path,
    letters_per_minute: float,
    typed_letters: int,
    duration_seconds: float,
    completed: bool,
    end_error_percentage: float,
    is_training_run: bool,
) -> None:
    """
    Store blind mode letter results including the end-error percentage.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    completed_flag = "1" if completed else "0"
    training_flag = "1" if is_training_run else "0"
    line = (
        f"{timestamp};{letters_per_minute:.3f};{typed_letters};"
        f"{duration_seconds:.3f};{completed_flag};"
        f"{end_error_percentage:.3f};{training_flag}\n"
    )
    ensure_stats_file_header(file_path, BLIND_LETTER_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_blind_special_result(
    file_path: Path,
    symbols_per_minute: float,
    typed_symbols: int,
    duration_seconds: float,
    completed: bool,
    end_error_percentage: float,
    is_training_run: bool,
) -> None:
    """
    Store blind mode special-character results with final error data.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    completed_flag = "1" if completed else "0"
    training_flag = "1" if is_training_run else "0"
    line = (
        f"{timestamp};{symbols_per_minute:.3f};{typed_symbols};"
        f"{duration_seconds:.3f};{completed_flag};"
        f"{end_error_percentage:.3f};{training_flag}\n"
    )
    ensure_stats_file_header(file_path, BLIND_SPECIAL_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)


def save_blind_number_result(
    file_path: Path,
    digits_per_minute: float,
    typed_digits: int,
    duration_seconds: float,
    completed: bool,
    end_error_percentage: float,
    is_training_run: bool,
) -> None:
    """
    Store blind mode number results with final error data.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    completed_flag = "1" if completed else "0"
    training_flag = "1" if is_training_run else "0"
    line = (
        f"{timestamp};{digits_per_minute:.3f};{typed_digits};"
        f"{duration_seconds:.3f};{completed_flag};"
        f"{end_error_percentage:.3f};{training_flag}\n"
    )
    ensure_stats_file_header(file_path, BLIND_NUMBER_STATS_FILE_HEADER)
    with file_path.open("a", encoding="utf-8") as stats_file:
        stats_file.write(line)
