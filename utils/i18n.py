"""Interface translations and system-language selection."""
from __future__ import annotations

import locale
import json
from pathlib import Path
import re
import os
import tkinter as tk
import textwrap
from tkinter import ttk, messagebox as _messagebox

TRANSLATIONS = {
    "Shift-required attempts": "Versuche mit Umschalttaste",
    "Shifted symbol confusion": "Verwechslung mit Umschalttaste",
    "Correct characters trend": "Trend korrekter Zeichen",
    "Correct letters trend": "Trend korrekter Buchstaben",
    "Correct symbols trend": "Trend korrekter Symbole",
    "Sudden death failed after": "Sofortiges Ende nach",
    "Time": "Zeit", "Suggested goal": "Empfohlenes Ziel", "line": "Zeile", "lines": "Zeilen",
    "characters": "Zeichen", "text": "Text", "Benchmark run.": "Vergleichslauf.",
    "Letters per minute and accuracy for letter drills.": "Buchstaben pro Minute und Genauigkeit bei Buchstabenübungen.",
    "Symbol speed and accuracy for character drills.": "Symbolgeschwindigkeit und Genauigkeit bei Zeichenübungen.",
    "Digits per minute and accuracy for number drills.": "Ziffern pro Minute und Genauigkeit bei Zahlenübungen.",
    "Trends and activity across all modes and sub-modes; uses the Runs filter.": "Trends und Aktivitäten für alle Modi; verwendet den Durchgangsfilter.",
    "Custom characters (case-sensitive; Enter and Tab may be included). Apply to use this set; repeated characters count once.": "Eigene Zeichen (Groß- und Kleinschreibung beachten; Eingabetaste und Tabulator können enthalten sein). Mit Anwenden übernehmen; wiederholte Zeichen zählen einmal.",
    "Determines coverage characters and the Letters / Characters / Numbers drill sets. Preset drills exclude characters needing composition or uncommon modifier combinations. Text languages do not filter coverage.": "Bestimmt die Zeichenabdeckung und die Übungssätze für Buchstaben, Zeichen und Zahlen. Voreingestellte Übungen schließen Zeichen mit zusammengesetzter Eingabe oder ungewöhnlichen Tastenkombinationen aus. Textsprachen filtern die Zeichenabdeckung nicht.",
    "Newly recorded finished runs only; Reset/switch/closure discard unfinished data. Paste/bulk edits are excluded. Same-hand Shift is a technique issue, separate from accuracy. Custom layouts have no physical Shift mapping. Timing excludes gaps over 5 seconds. Sparse samples stay visible but are excluded from summary ranking.": "Nur neu aufgezeichnete abgeschlossene Durchgänge; Zurücksetzen, Wechseln und Schließen verwerfen unvollständige Daten. Eingefügter Text und Masseneingaben sind ausgeschlossen. Die Umschalttaste mit derselben Hand ist ein Technikfehler, getrennt von der Genauigkeit. Benutzerdefinierte Layouts haben keine physische Umschalttasten-Zuordnung. Pausen über 5 Sekunden sind aus der Zeitmessung ausgeschlossen. Kleine Stichproben bleiben sichtbar, werden aber nicht eingestuft.",
    "Only this finished session is shown. Results are observations from one run. Same-hand Shift is a technique issue, separate from accuracy. Unavailable Shift information is not inferred. Timing excludes gaps over 5 seconds.": "Nur dieser abgeschlossene Durchgang wird angezeigt. Die Ergebnisse sind Beobachtungen eines Durchgangs. Die Umschalttaste mit derselben Hand ist ein Technikfehler, getrennt von der Genauigkeit. Fehlende Informationen über die Umschalttaste werden nicht geschätzt. Pausen über 5 Sekunden sind aus der Zeitmessung ausgeschlossen.",
    "All practice modes": "Alle Übungsmodi", "Cannot export report": "Bericht kann nicht exportiert werden",
    "Cannot generate text": "Text kann nicht generiert werden",
    "Cannot open Typing Trainer": "Tipptrainer kann nicht geöffnet werden",
    "Could not access user data": "Zugriff auf Benutzerdaten fehlgeschlagen", "Correct characters": "Korrekte Zeichen",
    "Correct digits trend": "Trend korrekter Ziffern", "Cumulative minutes": "Gesamte Minuten",
    "Daily time spent (": "Tägliche Übungszeit (", "Deleted characters": "Gelöschte Zeichen",
    "Letters per minute": "Buchstaben pro Minute", "Mistakes corrected": "Korrigierte Fehler",
    "Mistakes remaining": "Verbleibende Fehler", "No time recorded yet": "Noch keine Zeit erfasst",
    "Opposite-hand Shift": "Umschalttaste mit der anderen Hand", "Repeated character": "Wiederholtes Zeichen",
    "Starting LM Studio…": "LM Studio wird gestartet…", "Sudden-death failure": "Sofortiges Ende: Fehler",
    "Symbols per minute": "Zeichen pro Minute", "Time per month (min)": "Zeit pro Monat (Min.)",
    "Time spent by mode": "Übungszeit nach Modus", "correct (no limit)": "richtig (ohne Begrenzung)",
    "first-attempt errors": "Fehler beim ersten Versuch", "measured attempts.": "gemessene Versuche.",
    "Daily averages": "Tagesdurchschnitt", "error %": "Fehler %",
    "Latest session (individual)": "Letzter Durchgang (Einzelwert)",
    "Chapter": "Kapitel", "Selection": "Auswahl", "Information": "Information",
    "Unknown language": "Unbekannte Sprache", "statistics": "Statistik",
    "Joint WPM / error percentage distribution": "Gemeinsame Verteilung von WPM und Fehlerquote",
    "Cumulative error percentage trend": "Trend der kumulierten Fehlerquote",
    "Final error percentage trend": "Trend der endgültigen Fehlerquote",
    "App language": "App-Sprache", "System language": "Systemsprache", "Deutsch": "Deutsch",
    "Typing Trainer": "Tipptrainer", "Typing": "Tippen", "Typing text": "Text tippen",
    "Text management": "Textverwaltung", "Statistics": "Statistik", "Settings": "Einstellungen",
    "Helper modes": "Übungsmodi", "Mode": "Modus", "Training run": "Trainingslauf",
    "Available texts": "Verfügbare Texte", "Load random": "Zufälligen Text laden",
    "Generate text": "Text generieren", "Generated text language": "Sprache des generierten Textes",
    "Text to type": "Text zum Abtippen", "Character to type": "Einzugebendes Zeichen",
    "Your input": "Deine Eingabe", "Reset session": "Durchgang zurücksetzen",
    "Letters": "Buchstaben", "Characters": "Zeichen", "Numbers": "Zahlen",
    "Theme": "Darstellung", "System": "System", "Light": "Hell", "Dark": "Dunkel",
    "Practice text size": "Größe des Übungstexts", "UI text size": "Größe der Oberfläche",
    "Smaller": "Kleiner", "Reset": "Zurücksetzen", "Larger": "Größer",
    "Keyboard layout": "Tastaturlayout", "Apply custom characters": "Eigene Zeichen anwenden",
    "Charts": "Diagramme", "Mistake analysis": "Fehleranalyse", "Chart mode": "Diagrammmodus",
    "Runs": "Durchgänge", "Open report": "Bericht öffnen", "Overview": "Übersicht",
    "Mistakes current session": "Fehler des aktuellen Durchgangs",
    "Texts (drag to reorder)": "Texte (zum Sortieren ziehen)", "Text name": "Textname",
    "Language (required)": "Sprache (erforderlich)", "Language required": "Sprache erforderlich",
    "(unnamed)": "(unbenannt)", "Save changes": "Änderungen speichern",
    "Discard changes": "Änderungen verwerfen", "Close": "Schließen", "Add": "Hinzufügen",
    "Delete": "Löschen", "Move up": "Nach oben", "Move down": "Nach unten",
    "Character coverage": "Zeichenabdeckung", "Show counts below": "Anzahl kleiner als",
    "Apply": "Anwenden", "Refresh": "Aktualisieren", "Contents": "Inhalt",
    "Export PDF…": "PDF exportieren…", "History": "Zeitraum", "Practice": "Übung",
    "Layout": "Layout", "Language": "Sprache", "All": "Alle", "English": "Englisch",
    "German": "Deutsch", "Unknown": "Unbekannt", "Standard": "Standard",
    "Blind": "Blind", "Blind mode": "Blindmodus", "Sudden death": "Sofortiges Ende",
    "Training": "Training", "Benchmark": "Vergleich", "Training runs": "Trainingsläufe",
    "Non-training runs": "Vergleichsläufe", "All runs": "Alle Durchgänge",
    "Custom": "Benutzerdefiniert", "Last 7 days": "Letzte 7 Tage", "Last 30 days": "Letzte 30 Tage",
    "Last 90 days": "Letzte 90 Tage", "All history": "Gesamter Zeitraum",
    "Apply / Refresh": "Anwenden / Aktualisieren", "Minimum opportunities for ranking": "Mindestanzahl für die Rangliste",
    "Problem characters": "Problemzeichen", "Character categories": "Zeichenkategorien",
    "Confusions": "Verwechslungen", "Error types": "Fehlertypen", "Shift / corrections": "Umschalt / Korrekturen",
    "Transitions": "Übergänge", "Progress": "Fortschritt", "Character": "Zeichen",
    "Category": "Kategorie", "Whitespace": "Leerraum", "Digits": "Ziffern",
    "Uppercase letters": "Großbuchstaben", "Lowercase letters": "Kleinbuchstaben",
    "Punctuation / symbols": "Satzzeichen / Symbole", "Opportunities": "Vorkommen", "First errors": "Erste Fehler",
    "Error %": "Fehler %", "Mistakes": "Fehler", "Delay ms": "Verzögerung ms",
    "Evidence": "Datenlage", "Expected": "Erwartet", "Typed": "Eingetippt", "Count": "Anzahl",
    "Mistakes per 100 targets": "Fehler je 100 Zeichen", "Type": "Typ", "Metric": "Messwert",
    "Value": "Wert", "Pair": "Paar", "Samples": "Stichproben", "Average interval ms": "Mittleres Intervall ms",
    "Date": "Datum", "Same-hand Shift %": "Umschalt gleiche Hand %", "Enough data": "Genug Daten",
    "Not enough data": "Zu wenig Daten", "Performance trend": "Leistungstrend",
    "Performance by text language": "Leistung nach Textsprache", "Performance by previous text completions": "Leistung nach vorherigen Textdurchgängen",
    "Performance by text length": "Leistung nach Textlänge", "Latest session": "Letzter Durchgang",
    "Recorded session": "Aufgezeichneter Durchgang", "Session date": "Datum des Durchgangs",
    "Text language": "Textsprache", "Time": "Zeit", "Errors": "Fehler", "Error": "Fehler",
    "WPM distribution": "WPM-Verteilung", "Error percentage distribution": "Fehlerquotenverteilung",
    "Daily performance": "Tagesleistung", "Practice time": "Übungszeit", "Distributions": "Verteilungen",
    "Performance relationship": "Leistungszusammenhang", "Activity calendar": "Aktivitätskalender",
    "Practice breakdown": "Übungsaufteilung", "Average WPM": "Durchschnittliche WPM",
    "Average error %": "Durchschnittliche Fehler %", "Total time (min)": "Gesamtzeit (Min.)",
    "Time per day (min)": "Zeit pro Tag (Min.)", "Cumulative time (min)": "Gesamtzeit (Min.)",
    "Time spent per day": "Übungszeit pro Tag", "Words per minute": "Wörter pro Minute",
    "Frequency": "Häufigkeit", "Error percentage (%)": "Fehlerquote (%)",
    "System follows your desktop appearance. Light and Dark override it.": "System übernimmt die Darstellung des Desktops. Hell und Dunkel überschreiben sie.",
    "Size of practice passages and the text-manager editor.": "Größe der Übungstexte und des Texteditors.",
    "Size of labels, buttons, tabs, pickers and text names.": "Größe von Beschriftungen, Schaltflächen, Reitern, Auswahlfeldern und Textnamen.",
    "Changes are applied and saved automatically, except custom character edits.": "Änderungen werden automatisch angewendet und gespeichert, außer Änderungen an eigenen Zeichen.",
    "Edit text (wraps automatically; Enter adds a real newline)": "Text bearbeiten (automatischer Umbruch; Eingabetaste fügt einen Zeilenumbruch ein)",
    "Whitespace preview: · space   ⇥ tab   ↵ newline   ⟦…⟧ other invisible characters": "Leerzeichenvorschau: · Leerzeichen   ⇥ Tabulator   ↵ Zeilenumbruch   ⟦…⟧ andere unsichtbare Zeichen",
    "Changes are saved only when you click Save changes.": "Änderungen werden erst beim Klicken auf Änderungen speichern gesichert.",
    "Changes saved": "Änderungen gespeichert", "Changes discarded": "Änderungen verworfen",
    "Unsaved changes": "Ungespeicherte Änderungen", "Ready to type. Timing starts with the first character.": "Bereit zum Tippen. Die Zeitmessung beginnt mit dem ersten Zeichen.",
    "Load a text to begin.": "Lade einen Text, um zu beginnen.",
    "No texts yet. Add a passage in Text management.": "Noch keine Texte. Füge einen Text in der Textverwaltung hinzu.",
    "Choose a helper drill to begin.": "Wähle eine Übung, um zu beginnen.",
    "Choose Letters, Characters or Numbers to start a drill.": "Wähle Buchstaben, Zeichen oder Zahlen, um eine Übung zu starten.",
    "Standard: errors are highlighted; aim for accuracy.": "Standard: Fehler werden hervorgehoben; achte auf Genauigkeit.",
    "Sudden death: the first mistake ends the run.": "Sofortiges Ende: Der erste Fehler beendet den Durchgang.",
    "Blind mode: your input and live error feedback are hidden; review accuracy when the run ends.": "Blindmodus: Eingabe und Fehleranzeige sind verborgen; prüfe die Genauigkeit nach dem Durchgang.",
    "Click a text to load it, then type it. Enter is optional at automatic wraps; saved newlines require Enter.": "Klicke auf einen Text und tippe ihn ab. Bei automatischen Umbrüchen ist die Eingabetaste optional; gespeicherte Zeilenumbrüche erfordern sie.",
}


def effective_language(preference, system_language=None):
    if preference != "system":
        return preference
    if system_language is None:
        system_language = (os.environ.get("LANGUAGE", "").split(":")[0]
                           or os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
                           or os.environ.get("LANG")
                           or locale.getlocale(getattr(locale, "LC_MESSAGES", locale.LC_CTYPE))[0] or "")
    return "de" if system_language.lower().startswith("de") else "en"


with (Path(__file__).with_name("translations_de.json")).open(encoding="utf-8") as source:
    AUTOMATIC_TRANSLATIONS = json.load(source)
for original, translated in list(AUTOMATIC_TRANSLATIONS.items()):
    if "Sudden death" in original:
        translated = translated.replace("Plötzlicher Tod", "Sofortiges Ende").replace("plötzlicher Tod", "sofortiges Ende")
    if "Shift" in original:
        translated = translated.replace("Schicht", "Umschalttaste").replace("Shift", "Umschalttaste")
    AUTOMATIC_TRANSLATIONS[original] = translated
CATALOG = {**AUTOMATIC_TRANSLATIONS, **TRANSLATIONS}
SHORT_PHRASES = {"Chapter", "English", "German", "Unknown", "statistics", "Time",
                 "Suggested goal", "line", "lines", "characters", "text", "error %"}
PHRASE_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:" + "|".join(re.escape(key) for key in sorted(CATALOG, key=len, reverse=True)
                                  if len(key) >= 8 or key in SHORT_PHRASES) + r")(?![A-Za-z])"
)


def translate(text, language):
    if language != "de" or not text:
        return text
    if text in CATALOG:
        return CATALOG[text]
    plain = " ".join(text.split())
    match = re.fullmatch(r"Text context recorded for (\d+) of (\d+) sessions\. Older results have unknown context\.(?: Counts span practice modes and include training runs\.)?", plain)
    if match:
        result = f"Textdaten für {match[1]} von {match[2]} Durchgängen erfasst. Bei älteren Ergebnissen fehlen diese Daten."
        if "Counts span" in plain:
            result += " Die Anzahl umfasst alle Übungsmodi und Trainingsläufe."
        return textwrap.fill(result, 62) if "\n" in text else result
    match = re.fullmatch(r"Language available for (\d+) of (\d+) sessions; (\d+) recovered from uniquely matching mistake-analysis records\. Unmatched older sessions remain Unknown\. Single or constant groups appear as points\.", plain)
    if match:
        result = (f"Sprache für {match[1]} von {match[2]} Durchgängen verfügbar; {match[3]} aus eindeutig "
                  "zugeordneten Fehleranalysen ermittelt. Nicht zugeordnete ältere Durchgänge bleiben unbekannt. "
                  "Einzelne oder gleiche Werte werden als Punkte angezeigt.")
        return textwrap.fill(result, 62) if "\n" in text else result
    # Replace whole phrases in generated status messages without changing numbers.
    return PHRASE_PATTERN.sub(lambda match: CATALOG[match.group()], text)


_active_language = "en"


def set_message_language(language):
    global _active_language
    _active_language = language


class LocalizedMessagebox:
    def __getattr__(self, name):
        function = getattr(_messagebox, name)
        def show(title=None, message=None, **kwargs):
            return function(translate(title, _active_language), translate(message, _active_language), **kwargs)
        return show


messagebox = LocalizedMessagebox()


class Localizer:
    """Translate displayed labels while leaving control values and user text intact."""
    def __init__(self, root):
        self.root = root
        self.language = "en"
        self.original = {}
        self.tab_text = {}
        self.window_titles = {}
        self.variables = {}
        self.comboboxes = {}

    def apply(self, language):
        set_message_language(language)
        self.language = language
        self._visit(self.root)

    def _label_variable(self, widget):
        key = str(widget)
        if key not in self.variables:
            source = tk.StringVar(self.root, name=str(widget.cget("textvariable")))
            display = tk.StringVar(self.root)
            def sync(*_):
                display.set(translate(source.get(), self.language))
            source.trace_add("write", sync)
            self.variables[key] = (source, display, sync)
            widget.configure(textvariable=display)
        self.variables[key][2]()

    def _combobox(self, widget):
        key = str(widget)
        if key not in self.comboboxes:
            source = tk.StringVar(self.root, name=str(widget.cget("textvariable")))
            display = tk.StringVar(self.root)
            values = tuple(widget.cget("values"))
            state = {"syncing": False}
            def from_source(*_):
                if state["syncing"]:
                    return
                state["syncing"] = True
                display.set(translate(source.get(), self.language))
                state["syncing"] = False
            def from_display(*_):
                if state["syncing"]:
                    return
                text = display.get()
                state["syncing"] = True
                source.set(next((value for value in values if translate(value, self.language) == text), text))
                state["syncing"] = False
            source.trace_add("write", from_source)
            display.trace_add("write", from_display)
            self.comboboxes[key] = (source, display, values, from_source)
            widget.configure(textvariable=display)
        source, display, values, sync = self.comboboxes[key]
        widget.configure(values=[translate(value, self.language) for value in values])
        sync()

    def _visit(self, widget):
        try:
            if isinstance(widget, (tk.Tk, tk.Toplevel)):
                key = str(widget)
                current = widget.title()
                original = self.window_titles.get(key)
                if original is None or current not in (original, translate(original, "de")):
                    original = current
                    self.window_titles[key] = original
                widget.title(translate(original, self.language))
            if isinstance(widget, ttk.Notebook):
                for tab in widget.tabs():
                    key = (str(widget), tab)
                    current = widget.tab(tab, "text")
                    original = self.tab_text.get(key)
                    if original is None or current not in (original, translate(original, "de")):
                        original = current
                        self.tab_text[key] = original
                    widget.tab(tab, text=translate(original, self.language))
            if isinstance(widget, ttk.Combobox) and str(widget.cget("textvariable")):
                self._combobox(widget)
            if isinstance(widget, ttk.Label) and str(widget.cget("textvariable")):
                self._label_variable(widget)
            if isinstance(widget, (ttk.Label, ttk.Button, ttk.Checkbutton, ttk.Radiobutton, ttk.LabelFrame)):
                textvariable = str(widget.cget("textvariable")) if "textvariable" in widget.keys() else ""
                if not textvariable:
                    current = widget.cget("text")
                    key = str(widget)
                    original = self.original.get(key)
                    if original is None or current not in (original, translate(original, "de")):
                        original = current
                        self.original[key] = original
                    widget.configure(text=translate(original, self.language))
            if isinstance(widget, ttk.Treeview):
                for column in widget["columns"]:
                    current = widget.heading(column, "text")
                    # Sort indicators are managed separately; retain them.
                    suffix = " ↑" if current.endswith(" ↑") else " ↓" if current.endswith(" ↓") else ""
                    widget.heading(column, text=translate(column, self.language) + suffix)
            for child in widget.winfo_children():
                self._visit(child)
        except tk.TclError:
            return
