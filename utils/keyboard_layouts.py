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


def layout_characters(layout, custom=""):
    return "".join(dict.fromkeys(custom if layout == "Custom" else LAYOUTS[layout]))


def drill_characters(characters, kind):
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
