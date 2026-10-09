"""Session-local mistake tracking and encrypted, text-free aggregate history."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import json
import math
import time

from .io_utils import DataError, get__file_path, read_encrypted, write_encrypted
from .keyboard_layouts import character_key

ANALYSIS_FILE = "mistake_analysis.jsonl"
HISTORY_RANGES = ("Last 7 days", "Last 30 days", "Last 90 days", "All history")
ERROR_LABELS = {
    "missing_capital": "Missing capitalization", "unwanted_capital": "Unwanted capitalization",
    "substitution": "Character substitution", "omission": "Missing character",
    "extra": "Extra character", "repeat": "Repeated character", "transpose": "Transposed pair",
    "shift_symbol": "Shifted symbol confusion",
}


def category(char):
    if char.isspace():
        return "Whitespace"
    if char.isdecimal():
        return "Digits"
    if char.isalpha():
        return "Uppercase letters" if char.isupper() else "Lowercase letters"
    return "Punctuation / symbols"


def error_kind(expected, actual, layout):
    if not expected:
        return "extra"
    if not actual:
        return "omission"
    if expected != actual and expected.lower() == actual.lower():
        return "missing_capital" if expected.isupper() else "unwanted_capital"
    a, b = character_key(expected, layout), character_key(actual, layout)
    if a and b and a[0] == b[0] and a[2] != b[2]:
        return "shift_symbol"
    return "substitution"


def align_prefix(target, text, complete=False):
    """Banded edit alignment with free untyped suffix and adjacent swaps.

    Prefer substitutions until subsequent input provides evidence of an
    insertion/omission. This avoids cascades after a skipped character.
    None mappings denote extra input. Gaps exclude the still-untyped suffix.
    """
    n, m = len(target), len(text)
    if not m:
        return [], set(), set()
    width = max(24, abs(m - n) if m > n or complete else 0)
    scores, back = {(0, 0): 0}, {}
    for j in range(m + 1):
        for i in range(max(0, j - width), min(n, j + width) + 1):
            if i == j == 0:
                continue
            choices = []
            if i and j and (i - 1, j - 1) in scores:
                choices.append((scores[i - 1, j - 1] + (target[i - 1] != text[j - 1]), "match"))
            if i > 1 and j > 1 and target[i - 2:i] == text[j - 2:j][::-1] and target[i - 2] != target[i - 1] and (i - 2, j - 2) in scores:
                choices.append((scores[i - 2, j - 2] + 1, "swap"))
            if j and (i, j - 1) in scores:
                choices.append((scores[i, j - 1] + 1, "extra"))
            if i and (i - 1, j) in scores:
                choices.append((scores[i - 1, j] + 1, "gap"))
            if choices:
                scores[i, j], back[i, j] = min(choices, key=lambda entry: entry[0])
    endpoints = [(value, abs(i - m), i) for (i, j), value in scores.items() if j == m and (not complete or i == n)]
    _, _, i = min(endpoints)
    j = m
    mapping, gaps, swaps = [None] * m, set(), set()
    while i or j:
        operation = back[i, j]
        if operation == "match":
            mapping[j - 1] = i - 1
            i, j = i - 1, j - 1
        elif operation == "swap":
            mapping[j - 2:j] = [i - 2, i - 1]
            swaps.add((j - 2, j - 1))
            i, j = i - 2, j - 2
        elif operation == "gap":
            gaps.add(i - 1)
            i -= 1
        else:
            j -= 1
    return mapping, gaps, swaps


class MistakeRecorder:
    def __init__(self, target, metadata, clock=time.monotonic):
        self.target, self.metadata, self.clock = target, dict(metadata), clock
        self.text = ""
        self.tokens, self.retired, self.gaps, self.retired_gaps = [], [], {}, []
        self.swaps = set()
        self.attempts = []
        self.next_id = 0
        self.last_time = None
        self.backspaces = self.deleted = self.pauses = 0
        self.excluded = False

    def _token(self, char, modifiers):
        now = self.clock()
        delay = None if self.last_time is None else (now - self.last_time) * 1000
        if delay is not None and delay > 5000:
            self.pauses += 1
            delay = None
        self.last_time = now
        self.next_id += 1
        return {"id": self.next_id, "char": char, "time": now, "delay": delay,
                "modifiers": modifiers, "position": None, "error": False, "swap": None}

    def observe(self, text, modifiers=None):
        if text == self.text:
            return
        previous, tokens = self.tokens, []
        for op, a, b, c, d in SequenceMatcher(None, self.text, text, autojunk=False).get_opcodes():
            if op == "equal":
                tokens.extend(previous[a:b])
            else:
                self.deleted += b - a
                for token in previous[a:b]:
                    token = dict(token, removed=self.clock())
                    self.retired.append(token)
                for char in text[c:d]:
                    tokens.append(self._token(char, modifiers if d - c == 1 else None))
        self.text, self.tokens = text, tokens
        self._remap()

    def _remap(self, complete=False):
        text, tokens = self.text, self.tokens
        if text == self.target or (not complete and text == self.target[:len(text)]):
            mapping, gaps, swaps = list(range(len(text))), set(), set()
        else:
            mapping, gaps, swaps = align_prefix(self.target, text, complete)
        for index, (token, position) in enumerate(zip(tokens, mapping)):
            token["position"] = position
            token["error"] = position is None or token["char"] != self.target[position]
            token["swap"] = None
            token["repeat"] = position is None and ((index > 0 and text[index - 1] == token["char"]) or (index + 1 < len(text) and text[index + 1] == token["char"]))
        now = self.clock()
        for position in set(self.gaps) - gaps:
            self.retired_gaps.append((position, self.gaps[position], now))
            del self.gaps[position]
        for position in gaps:
            self.gaps.setdefault(position, now)
        self.swaps = {(tokens[a]["id"], tokens[b]["id"]) for a, b in swaps}
        for a, b in swaps:
            tokens[a]["swap"] = tokens[b]["swap"] = (tokens[a]["id"], tokens[b]["id"])

    def attempt(self, position, expected, actual, modifiers=None):
        token = self._token(actual, modifiers)
        token.update(position=position, error=expected != actual, expected=expected)
        self.attempts.append(token)

    def undo(self, position):
        for token in reversed(self.attempts):
            if token["position"] == position and "removed" not in token:
                token["removed"] = self.clock()
                self.deleted += 1
                return

    def backspace(self):
        self.backspaces += 1

    def finish(self, final_text=None):
        if self.excluded:
            return None
        direct = bool(self.attempts)
        if not direct and final_text is not None:
            self.observe(final_text)
        if not direct:
            self._remap(complete=True)
        tokens = self.attempts if direct else self.retired + self.tokens
        if not tokens:
            return None
        target = self.target
        characters = {c: {"opportunities": count, "first_errors": 0, "mistakes": 0,
                          "delay_count": 0, "delay_ms": 0.0} for c, count in Counter(target).items()}
        first, kinds, confusions, shift, transitions = {}, Counter(), Counter(), Counter(), defaultdict(lambda: [0, 0.0])
        corrections = {"backspaces": self.backspaces, "deleted_characters": self.deleted,
                       "corrected": 0, "remaining": 0, "recovery_count": 0, "recovery_ms": 0.0}
        active_ids = {t["id"] for t in self.tokens}
        final_by_position = defaultdict(list)
        for token in tokens:
            if token["position"] is not None:
                final_by_position[token["position"]].append(token)
        swaps = {t["swap"] for t in tokens if t.get("swap")}
        swapped_ids = {value for pair in swaps for value in pair}
        kinds["transpose"] = len(swaps)
        previous = None
        timed_positions = set()
        for token in sorted(tokens, key=lambda t: t["id"]):
            pos = token["position"]
            expected = target[pos] if pos is not None else ""
            actual = token["char"]
            if pos is not None:
                first.setdefault(pos, token["error"])
                values = characters[expected]
                if token["delay"] is not None and pos not in timed_positions:
                    values["delay_count"] += 1
                    values["delay_ms"] += token["delay"]
                timed_positions.add(pos)
                self._shift_counts(expected, token["modifiers"], shift)
            if token["error"]:
                kind = error_kind(expected, actual, self.metadata["layout"])
                if token["id"] not in swapped_ids:
                    if not expected and token.get("repeat"):
                        kind = "repeat"
                    kinds[kind] += 1
                    if expected and actual:
                        confusions[expected, actual] += 1
                modifiers = token["modifiers"]
                if modifiers and not modifiers.get("caps"):
                    if kind == "missing_capital" and modifiers.get("shift") == "none":
                        shift["missing_shift"] += 1
                    if kind == "unwanted_capital" and modifiers.get("shift") in ("left", "right", "both"):
                        shift["extra_shift"] += 1
                if expected:
                    characters[expected]["mistakes"] += 1
                later = [t for t in final_by_position[pos] if t["id"] > token["id"] and not t["error"]] if pos is not None else []
                fixed = bool(later) or "removed" in token if direct else token["id"] not in active_ids
                corrections["corrected" if fixed else "remaining"] += 1
                end = later[0]["time"] if later else token.get("removed")
                if fixed and end is not None:
                    corrections["recovery_count"] += 1
                    corrections["recovery_ms"] += max(0, (end - token["time"]) * 1000)
            if previous and pos is not None and previous["position"] == pos - 1 and not previous["error"] and not token["error"] and token["delay"] is not None:
                pair = target[pos - 1:pos + 1]
                transitions[pair][0] += 1
                transitions[pair][1] += token["delay"]
            previous = token
        for pos, start, end in self.retired_gaps + [(p, start, None) for p, start in self.gaps.items()]:
            first[pos] = True
            characters[target[pos]]["mistakes"] += 1
            kinds["omission"] += 1
            corrections["corrected" if end is not None else "remaining"] += 1
        for position, wrong in first.items():
            characters[target[position]]["first_errors"] += int(wrong)
        return {"version": 1, "timestamp": datetime.now().astimezone().isoformat(), **self.metadata,
                "characters": characters, "errors": dict(kinds),
                "confusions": [[a, b, count] for (a, b), count in confusions.items()],
                "shift": dict(shift), "corrections": corrections, "pauses": self.pauses,
                "transitions": [[pair, count, round(ms, 3)] for pair, (count, ms) in transitions.items()]}

    def _shift_counts(self, char, modifiers, counts):
        key = character_key(char, self.metadata["layout"])
        if not key:
            if char.isupper():
                counts["opportunities"] += 1
                counts["unknown"] += 1
            return
        if not key[2]:
            return
        counts["opportunities"] += 1
        if modifiers is None:
            counts["unknown"] += 1
            return
        side = modifiers.get("shift", "unknown")
        if modifiers.get("caps") and char.isalpha():
            counts["caps_lock"] += 1
        elif side in ("left", "right"):
            counts[side] += 1
            counts["opposite_hand" if side != key[1] else "same_hand"] += 1
        else:
            counts[side if side in ("none", "both") else "unknown"] += 1


def load_analysis():
    path = get__file_path(ANALYSIS_FILE)
    if not path.exists():
        return []
    try:
        records = [json.loads(line) for line in read_encrypted(path).splitlines() if line.strip()]
        for record in records:
            if record.get("version") != 1 or not isinstance(record.get("characters"), dict):
                raise ValueError
            if datetime.fromisoformat(record["timestamp"]).tzinfo is None:
                raise ValueError
            if record["mode"] not in ("typing", "letter", "special", "number") or record["variant"] not in ("standard", "blind", "sudden") or type(record["training"]) is not bool or not isinstance(record["layout"], str):
                raise ValueError
            for char, values in record["characters"].items():
                if len(char) != 1 or values["opportunities"] < 1 or not 0 <= values["first_errors"] <= values["opportunities"]:
                    raise ValueError
                for key in ("opportunities", "first_errors", "mistakes", "delay_count", "delay_ms"):
                    if not isinstance(values[key], (int, float)) or not math.isfinite(values[key]) or values[key] < 0:
                        raise ValueError
            for key in ("errors", "shift", "corrections"):
                if not isinstance(record[key], dict) or any(not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in record[key].values()):
                    raise ValueError
            if any(key not in ERROR_LABELS for key in record["errors"]):
                raise ValueError
            for expected, actual, count in record["confusions"]:
                if len(expected) != 1 or len(actual) != 1 or expected not in record["characters"] or type(count) is not int or count < 1:
                    raise ValueError
            for pair, count, ms in record["transitions"]:
                if len(pair) != 2 or type(count) is not int or count < 1 or not isinstance(ms, (int, float)) or not math.isfinite(ms) or ms < 0:
                    raise ValueError
        return records
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise DataError("Cannot read mistake analysis. Restore a valid backup.") from error


def save_analysis(record):
    # Validate existing history before appending; never overwrite damaged data.
    records = load_analysis()
    records.append(record)
    write_encrypted(get__file_path(ANALYSIS_FILE), "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n")


def filter_records(records, history="Last 30 days", mode="All", variant="All", layout="All", language="All", training="All", now=None):
    now = now or datetime.now().astimezone()
    days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}.get(history)
    return [r for r in records
            if (days is None or datetime.fromisoformat(r["timestamp"]) >= now - timedelta(days=days))
            and (mode == "All" or r["mode"] == mode)
            and (variant == "All" or r["variant"] == variant)
            and (layout == "All" or r["layout"] == layout)
            and (language == "All" or (r.get("language") or "Unknown") == language)
            and (training == "All" or r["training"] == (training == "Training"))]


def aggregate(records):
    chars = defaultdict(Counter)
    errors, shifts, corrections, confusions, transitions = Counter(), Counter(), Counter(), Counter(), defaultdict(lambda: [0, 0.0])
    for record in records:
        for char, metrics in record["characters"].items():
            chars[char].update(metrics)
        errors.update(record["errors"])
        shifts.update(record["shift"])
        corrections.update(record["corrections"])
        for a, b, count in record["confusions"]:
            confusions[a, b] += count
        for pair, count, ms in record["transitions"]:
            transitions[pair][0] += count
            transitions[pair][1] += ms
    return {"characters": chars, "errors": errors, "shift": shifts, "corrections": corrections,
            "confusions": confusions, "transitions": transitions, "runs": len(records)}


def findings(data, minimum=30):
    chars = data["characters"]
    eligible = [(v["first_errors"] / v["opportunities"], c, v) for c, v in chars.items() if v["opportunities"] >= minimum and v["first_errors"]]
    output = []
    if eligible:
        rate, char, values = max(eligible)
        output.append(f"Highest first-attempt error rate: {char!r}, {rate:.1%} ({values['first_errors']}/{values['opportunities']}).")
    categories = defaultdict(Counter)
    for char, values in chars.items():
        categories[category(char)].update(values)
    letters = categories["Lowercase letters"] + categories["Uppercase letters"]
    if letters["opportunities"] >= minimum:
        baseline = letters["first_errors"] / letters["opportunities"]
        comparisons = [(values["first_errors"] / values["opportunities"], name)
                       for name, values in categories.items() if name in ("Digits", "Punctuation / symbols", "Whitespace") and values["opportunities"] >= minimum]
        if comparisons:
            rate, name = max(comparisons)
            if rate > baseline:
                output.append(f"{name}: {rate:.1%} first-attempt errors, versus {baseline:.1%} for letters.")
    eligible_confusions = [(pair, count) for pair, count in data["confusions"].most_common()
                          if chars[pair[0]]["opportunities"] >= minimum]
    if eligible_confusions:
        (expected, actual), count = eligible_confusions[0]
        output.append(f"Most frequent confusion: {expected!r} → {actual!r}, {count} times.")
    shift = data["shift"]
    measured = shift["same_hand"] + shift["opposite_hand"]
    if measured >= minimum and shift["same_hand"]:
        output.append(f"Shift technique: same-hand Shift on {shift['same_hand']}/{measured} measured attempts.")
    if not output:
        output.append("No recurring weakness established yet. Complete more runs to gather evidence.")
    return output[:3]
