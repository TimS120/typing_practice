"""Backward-compatible text context stored with encrypted statistics."""
import csv
import hashlib
from pathlib import Path

from .io_utils import open_encrypted_stats


def read_results(path: Path) -> list[dict]:
    """Read old and new rows without inventing missing context."""
    if not path.exists():
        return []
    with open_encrypted_stats(path) as stream:
        return list(csv.DictReader(stream, delimiter=";"))


def text_context(path: Path, details: dict | None) -> str:
    if not details:
        return ";;;;"
    text = details["text"]
    identity = hashlib.sha256(text.encode("utf-8")).hexdigest()
    previous = 0
    for name in ("typing_stats.csv.enc", "sudden_death_typing_stats.csv.enc", "blind_typing_stats.csv.enc"):
        for row in read_results(path.parent / name):
            if row.get("text_id") == identity and row.get("completed", "1") == "1":
                previous += 1
    language = details.get("language", "")
    if language not in ("English", "German"):
        language = ""
    return f";{language};{identity};{len(text)};{previous}"



def recover_languages(path: Path, rows: list[dict], analysis: list[dict]) -> list[dict]:
    """Join uniquely matching historical sessions, without changing saved files.

    Old CSV rows have no shared ID. Require an exact local timestamp, practice
    variant, training flag and outcome, with a single row on each side.
    """
    from collections import Counter, defaultdict
    from datetime import datetime

    variants = {"typing_stats.csv.enc": "standard", "sudden_death_typing_stats.csv.enc": "sudden",
                "blind_typing_stats.csv.enc": "blind"}
    variant = variants.get(path.name)
    if variant is None:
        return rows

    def row_key(row):
        training = str(row.get("is_training_run", "")).lower() in ("1", "true", "yes", "y")
        outcome = "Completed" if row.get("completed", "1") == "1" else "Sudden-death failure"
        return row.get("timestamp"), variant, training, outcome

    counts = Counter(row_key(row) for row in rows)
    candidates = defaultdict(list)
    for record in analysis:
        if record.get("mode") != "typing":
            continue
        try:
            timestamp = datetime.fromisoformat(record["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        except (KeyError, TypeError, ValueError):
            continue
        key = timestamp, record.get("variant"), record.get("training"), record.get("outcome")
        candidates[key].append(record)
    result = []
    for row in rows:
        key = row_key(row)
        matches = candidates[key]
        if not row.get("language") and counts[key] == 1 and len(matches) == 1:
            language = matches[0].get("language")
            if language in ("English", "German"):
                row = dict(row, language=language, _language_source="mistake analysis")
        result.append(row)
    return result
