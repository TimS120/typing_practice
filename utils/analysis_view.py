"""Themed mistake reports with selectable history and practice filters."""
from collections import Counter
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from .keyboard_layouts import LAYOUTS, character_label
from .mistake_analysis import HISTORY_RANGES, ERROR_LABELS, aggregate, category, filter_records, findings, load_analysis


class AnalysisView:
    def __init__(self, app, parent, session_record=None):
        self.app = app
        self.session_record = session_record
        self.page = ttk.Frame(parent, padding=10)
        self.page.pack(fill="both", expand=True)
        self.page.columnconfigure(0, weight=1)
        self.page.rowconfigure(4, weight=1)
        self.variables = {}
        if session_record is None:
            controls = ttk.Frame(self.page)
            controls.grid(row=0, column=0, sticky="ew")
            options = (
                ("History", HISTORY_RANGES, app.analysis_history),
                ("Practice", ("All", "Typing text", "Letters", "Characters", "Numbers"), "All"),
                ("Mode", ("All", "Standard", "Blind", "Sudden death"), "All"),
                ("Runs", ("All", "Training", "Benchmark"), "All"),
                ("Layout", ("All", *LAYOUTS, "Custom"), app.keyboard_layout_var.get()),
                ("Language", ("All", "English", "German", "Unknown"), "All"),
            )
            for index, (label, values, initial) in enumerate(options):
                container = ttk.Frame(controls)
                container.grid(row=index // 3, column=index % 3, sticky="ew", padx=(0, 10), pady=3)
                controls.columnconfigure(index % 3, weight=1)
                ttk.Label(container, text=label).pack(anchor="w")
                var = tk.StringVar(parent, value=initial)
                self.variables[label] = var
                picker = ttk.Combobox(container, textvariable=var, values=values, state="readonly", font=app.ui_font)
                picker.pack(fill="x")
                picker.bind("<<ComboboxSelected>>", self.changed)
            settings = ttk.Frame(self.page)
            settings.grid(row=1, column=0, sticky="ew", pady=6)
            ttk.Label(settings, text="Minimum opportunities for ranking").pack(side="left")
            self.minimum = tk.StringVar(parent, value=str(app.analysis_minimum))
            ttk.Entry(settings, textvariable=self.minimum, width=6).pack(side="left", padx=6)
            ttk.Button(settings, text="Apply / Refresh", command=self.refresh).pack(side="left")
        else:
            mode = {"typing": "Typing text", "letter": "Letters", "special": "Characters", "number": "Numbers"}[session_record["mode"]]
            variant = {"standard": "Standard", "blind": "Blind", "sudden": "Sudden death"}[session_record["variant"]]
            metadata = " · ".join((mode, variant, session_record["layout"], session_record.get("language") or "Unknown language",
                                   "Training" if session_record["training"] else "Benchmark", session_record["outcome"]))
            self.metadata_label = ttk.Label(self.page, text=metadata, wraplength=1000)
            self.metadata_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.summary = tk.StringVar(parent)
        self.summary_label = ttk.Label(self.page, textvariable=self.summary, wraplength=1000)
        self.summary_label.grid(row=2, column=0, sticky="ew", pady=(2, 6))
        self.note = ttk.Label(self.page, text="Newly recorded finished runs only; Reset/switch/closure discard unfinished data. "
                              "Paste/bulk edits are excluded. Same-hand Shift is a technique issue, separate from accuracy. "
                              "Custom layouts have no physical Shift mapping. Timing excludes gaps over 5 seconds. Sparse samples stay visible but are not ranked.", wraplength=1000)
        if session_record is not None:
            self.note.configure(text="Only this finished session is shown. Results are observations from one run. "
                                "Same-hand Shift is a technique issue, separate from accuracy. "
                                "Unavailable Shift information is not inferred. Timing excludes gaps over 5 seconds.")
        self.note.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.tabs = ttk.Notebook(self.page)
        self.tabs.grid(row=4, column=0, sticky="nsew")
        self.tables = {}
        for key, title, columns in (
            ("characters", "Problem characters", ("Character", "Category", "Opportunities", "First errors", "Error %", "Mistakes", "Delay ms", "Evidence")),
            ("categories", "Character categories", ("Category", "Opportunities", "First errors", "Error %")),
            ("confusions", "Confusions", ("Expected", "Typed", "Count", "Mistakes per 100 targets", "Type")),
            ("errors", "Error types", ("Type", "Count")),
            ("technique", "Shift / corrections", ("Metric", "Value")),
            ("transitions", "Transitions", ("Pair", "Samples", "Average interval ms", "Evidence")),
            ("progress", "Progress", ("Date", "Runs", "Opportunities", "First errors", "Error %", "Same-hand Shift %")),
        ):
            if session_record is not None:
                if key == "progress":
                    continue
                columns = tuple(column for column in columns if column != "Evidence")
            page = ttk.Frame(self.tabs)
            page.columnconfigure(0, weight=1)
            page.rowconfigure(0, weight=1)
            self.tabs.add(page, text=title)
            table = ttk.Treeview(page, columns=columns, show="headings", style="Coverage.Treeview")
            for column in columns:
                table.heading(column, text=column, command=lambda t=table, c=column: self.sort(t, c))
                table.column(column, width=125, minwidth=65, stretch=True)
            table.grid(row=0, column=0, sticky="nsew")
            vertical = ttk.Scrollbar(page, command=table.yview)
            vertical.grid(row=0, column=1, sticky="ns")
            horizontal = ttk.Scrollbar(page, orient="horizontal", command=table.xview)
            horizontal.grid(row=1, column=0, sticky="ew")
            table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
            self.tables[key] = table
        self.page.bind("<Configure>", self.resize)
        self.records = []
        self.data = aggregate([])
        self.refresh(save=False)

    def resize(self, event):
        if event.widget is self.page:
            for widget in (self.note, self.summary_label):
                widget.configure(wraplength=max(200, event.width - 25))
            if self.session_record is not None:
                self.metadata_label.configure(wraplength=max(200, event.width - 25))

    def changed(self, event):
        event.widget.selection_clear()
        self.refresh()

    def refresh(self, save=True):
        if self.session_record is not None:
            self.records = [self.session_record]
            self.data = aggregate(self.records)
            opportunities = sum(v["opportunities"] for v in self.data["characters"].values())
            errors = sum(v["first_errors"] for v in self.data["characters"].values())
            observations = findings(self.data, 1) if errors or self.data["shift"]["same_hand"] else ["No typing mistakes or measured Shift technique errors recorded."]
            self.summary.set(f"This session · {opportunities} opportunities · {errors / opportunities:.1%} first-attempt errors\n" + "\n".join(observations))
            self.render(1)
            return
        try:
            minimum = int(self.minimum.get())
            if minimum < 1:
                raise ValueError
        except ValueError:
            self.summary.set("Enter a positive whole number for minimum opportunities.")
            return
        try:
            records = load_analysis()
        except (ValueError, OSError) as error:
            messagebox.showerror("Mistake analysis", str(error), parent=self.app.master)
            return
        self.app.analysis_history = self.variables["History"].get()
        self.app.analysis_minimum = minimum
        if save:
            self.app._save_preferences()
        mode = {"Typing text": "typing", "Letters": "letter", "Characters": "special", "Numbers": "number"}.get(self.variables["Practice"].get(), "All")
        variant = {"Standard": "standard", "Blind": "blind", "Sudden death": "sudden"}.get(self.variables["Mode"].get(), "All")
        self.records = filter_records(records, history=self.app.analysis_history, mode=mode, variant=variant,
                                      layout=self.variables["Layout"].get(), language=self.variables["Language"].get(), training=self.variables["Runs"].get())
        self.data = aggregate(self.records)
        opportunities = sum(v["opportunities"] for v in self.data["characters"].values())
        first_errors = sum(v["first_errors"] for v in self.data["characters"].values())
        self.summary.set(f"{len(self.records)} finished runs · {opportunities} opportunities · "
                         f"{first_errors / opportunities:.1%} first-attempt errors\n" + "\n".join(findings(self.data, minimum)) if opportunities else
                         "No analysis data for these filters yet. Complete a run to start collecting details; older statistics cannot be reconstructed.")
        self.render(minimum)

    def render(self, minimum):
        for table in self.tables.values():
            table.delete(*table.get_children())
        def insert(key, *values):
            if self.session_record is not None and key in ("characters", "transitions"):
                values = values[:-1]
            self.tables[key].insert("", "end", values=values)
        categories = {}
        for char, values in sorted(self.data["characters"].items(), key=lambda row: (row[1]["opportunities"] < minimum, -row[1]["first_errors"] / row[1]["opportunities"], row[0])):
            opportunities = values["opportunities"]
            insert("characters", character_label(char), category(char), opportunities, values["first_errors"],
                   f"{values['first_errors'] / opportunities * 100:.1f}", values["mistakes"],
                   f"{values['delay_ms'] / values['delay_count']:.0f}" if values["delay_count"] else "—",
                   "Enough data" if opportunities >= minimum else "Not enough data")
            categories.setdefault(category(char), Counter()).update(values)
        for name, values in categories.items():
            insert("categories", name, values["opportunities"], values["first_errors"], f"{values['first_errors'] / values['opportunities'] * 100:.1f}")
        for (expected, actual), count in self.data["confusions"].most_common():
            from .mistake_analysis import error_kind
            layout = self.session_record["layout"] if self.session_record is not None else self.variables["Layout"].get()
            kind = error_kind(expected, actual, layout)
            denominator = self.data["characters"][expected]["opportunities"]
            insert("confusions", character_label(expected), character_label(actual), count,
                   f"{count / denominator * 100:.1f}", ERROR_LABELS[kind])
        for kind, count in self.data["errors"].most_common():
            if count:
                insert("errors", ERROR_LABELS[kind], count)
        shift = self.data["shift"]
        measured = shift["same_hand"] + shift["opposite_hand"]
        for name, key in (("Shift-required attempts", "opportunities"), ("Left Shift", "left"), ("Right Shift", "right"),
                          ("Opposite-hand Shift", "opposite_hand"), ("Same-hand Shift (technique error)", "same_hand"),
                          ("Caps Lock on uppercase letters", "caps_lock"), ("Shift not held", "none"),
                          ("Both Shift keys", "both"), ("Shift side / physical mapping unavailable", "unknown"),
                          ("Capitalization errors with Shift not held", "missing_shift"),
                          ("Capitalization errors with unwanted Shift", "extra_shift")):
            insert("technique", name, shift[key])
        insert("technique", "Same-hand rate among known single-Shift attempts", f"{shift['same_hand'] / measured:.1%}" if measured else "Unknown")
        correction = self.data["corrections"]
        for key, title in (("corrected", "Mistakes corrected"), ("remaining", "Mistakes remaining"),
                           ("backspaces", "Backspace presses"), ("deleted_characters", "Deleted characters")):
            insert("technique", title, correction[key])
        insert("technique", "Average recovery time ms", f"{correction['recovery_ms'] / correction['recovery_count']:.0f}" if correction["recovery_count"] else "—")
        for pair, (count, ms) in sorted(self.data["transitions"].items(), key=lambda item: (item[1][0] < minimum, -item[1][1] / item[1][0])):
            insert("transitions", " → ".join(character_label(c) for c in pair), count, f"{ms / count:.0f}",
                   "Enough data" if count >= minimum else "Not enough data")
        if self.session_record is not None:
            return
        dates = {}
        for record in self.records:
            day = datetime.fromisoformat(record["timestamp"]).astimezone().date().isoformat()
            dates.setdefault(day, []).append(record)
        for day, records in sorted(dates.items()):
            data = aggregate(records)
            n = sum(v["opportunities"] for v in data["characters"].values())
            errors = sum(v["first_errors"] for v in data["characters"].values())
            known = data["shift"]["same_hand"] + data["shift"]["opposite_hand"]
            insert("progress", day, len(records), n, errors, f"{errors / n * 100:.1f}" if n else "—",
                   f"{data['shift']['same_hand'] / known * 100:.1f}" if known else "Unknown")

    @staticmethod
    def sort(table, column):
        def key(item):
            value = table.set(item, column)
            try:
                return 0, float(value)
            except ValueError:
                return 1, value
        reverse = getattr(table, "_sort_column", None) == column and not getattr(table, "_sort_reverse", False)
        table._sort_column, table._sort_reverse = column, reverse
        for index, item in enumerate(sorted(table.get_children(), key=key, reverse=reverse)):
            table.move(item, "", index)
