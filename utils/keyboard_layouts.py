"""Explicit practice repertoires; coverage never filters texts by language."""
from collections import Counter
import string
import unicodedata

LAYOUTS = {
    "German QWERTZ": string.ascii_letters + string.digits + string.punctuation + "äöüÄÖÜßẞ€§°²³µ´" + " \t\n",
    "US QWERTY": string.ascii_letters + string.digits + string.punctuation + " \t\n",
    "UK QWERTY": string.ascii_letters + string.digits + string.punctuation + "£¬¦€" + " \t\n",
}
DEFAULT_LAYOUT = "German QWERTZ"


def keyboard_can_type(char, layout, custom=""):
    """Approximate standard layouts, including their common dead-key compositions.

    Custom is an explicit repertoire, not a detected physical keyboard. OS
    variants, input methods and remappings can differ from these presets.
    """
    if layout == "Custom":
        return char in custom
    if layout not in LAYOUTS:
        return False
    direct = LAYOUTS[layout].replace("ẞ", "") if layout == "German QWERTZ" else LAYOUTS[layout]
    if char in direct:
        return True
    if layout == "German QWERTZ":
        decomposed = unicodedata.normalize("NFD", char)
        return (len(decomposed) == 2 and decomposed[0] in string.ascii_letters
                and decomposed[1] in "\u0300\u0301\u0302")
    return False

# Preset drills use ordinary keys, Shift or AltGr, without composition,
# dead-key sequences, lock-state tricks or Shift+AltGr combinations. Keep
# coverage repertoires separate: saved texts may still contain these symbols.
DRILL_EXCLUSIONS = {
    "German QWERTZ": frozenset("ẞ^`´"),
    "US QWERTY": frozenset(),
    "UK QWERTY": frozenset("¦"),
}


def layout_characters(layout, custom=""):
    return "".join(dict.fromkeys(custom if layout == "Custom" else LAYOUTS[layout]))


def drill_characters(characters, kind, layout=None):
    excluded = DRILL_EXCLUSIONS.get(layout, frozenset())
    characters = "".join(c for c in characters if c not in excluded)
    if kind == "letter":
        return "".join(c for c in characters if c.isalpha())
    if kind == "number":
        return "".join(c for c in characters if c.isdecimal())
    return "".join(c for c in characters if not c.isalpha() and not c.isdecimal() and not c.isspace()
                   and not unicodedata.category(c).startswith("C"))


def character_coverage(entries, characters, threshold):
    counts = Counter(c for entry in entries for c in entry["text"])
    return sorted(((c, counts[c]) for c in dict.fromkeys(characters)
                   if counts[c] < threshold), key=lambda row: (row[1], ord(row[0])))


def character_label(char):
    labels = {" ": "Space", "\t": "Tab", "\n": "Enter / newline"}
    return labels.get(char, char if char.isprintable() else unicodedata.name(char, "Control"))


def character_key(char, layout):
    """Return (base key, typing hand, Shift required) for conventional layouts.

    Custom repertoires have no physical mapping. AltGr-only and composed
    characters are intentionally not assigned a Shift technique.
    """
    if layout not in LAYOUTS:
        return None
    lower = char.lower()
    left = "qwertasdfgzxcvb" if layout != "German QWERTZ" else "qwertasdfgyxcvb"
    right = "yuiophjklnm" if layout != "German QWERTZ" else "zuiophjklnmäöü"
    if len(lower) == 1 and lower in left + right:
        return lower, "left" if lower in left else "right", char.isupper()
    digits = "1234567890"
    shifted = '!@#$%^&*()' if layout == "US QWERTY" else '!"£$%^&*()' if layout == "UK QWERTY" else '!"§$%&/()='
    pairs = list(zip(digits, shifted, ["left"] * 5 + ["right"] * 5))
    if layout == "German QWERTZ":
        pairs += [("ß", "?", "right"), ("+", "*", "right"), ("#", "'", "right"),
                  (",", ";", "right"), (".", ":", "right"), ("-", "_", "right"),
                  ("<", ">", "left"), ("^", "°", "left")]
    else:
        pairs += [("-", "_", "right"), ("=", "+", "right"), ("[", "{", "right"),
                  ("]", "}", "right"), (";", ":", "right"), (",", "<", "right"),
                  (".", ">", "right"), ("/", "?", "right")]
        pairs += [("'", '@', "right"), ("#", "~", "right"), ("`", "¬", "left"), ("\\", "|", "left")] if layout == "UK QWERTY" else [("'", '"', "right"), ("`", "~", "left"), ("\\", "|", "right")]
    for base, upper, hand in pairs:
        if char in (base, upper):
            return base, hand, char == upper
    return None
