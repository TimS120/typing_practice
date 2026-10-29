"""Scrollable chart reports and optional text context for encrypted results."""
from __future__ import annotations

from datetime import datetime
import math
import textwrap
import tkinter as tk
from tkinter import ttk, filedialog
from .i18n import messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import numpy as np


from .statistics_data import read_results, recover_languages
from .i18n import translate


def trend(ax, x, y, color=None):
    """Fit observations only; never treat days without practice as zero speed."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if len(x) < 2 or np.ptp(x) == 0:
        return False
    origin = x.min()
    slope, intercept = np.polyfit(x - origin, y, 1)
    limits = np.array([x.min(), x.max()])
    ax.plot(limits, slope * (limits - origin) + intercept, "--", color=color,
            label="Linear trend (descriptive)")
    ax.legend()
    return True


def language_violins(ax, groups, labels):
    """Show observed distributions; a single/constant sample has no density."""
    for position, group in enumerate(groups, 1):
        if len(group) >= 2 and np.ptp(group) > 0:
            parts = ax.violinplot([group], positions=[position], showmedians=True,
                                  showextrema=True, widths=0.75)
            for body in parts["bodies"]:
                body.set_facecolor("#add8e6")
                body.set_edgecolor("#6faac0")
                body.set_alpha(0.85)
            for name in ("cmedians", "cmins", "cmaxes", "cbars"):
                parts[name].set_color("#6faac0")
        else:
            ax.scatter([position] * len(group), group, color="#add8e6",
                       edgecolors="#6faac0", s=45, zorder=3)
    ax.set_xticks(range(1, len(groups) + 1), labels)
    ax.set_xlim(0.4, len(groups) + 0.6)
    ax.margins(y=0.125)


def context_figures(app, paths, speed_label):
    rows = []
    analysis = None
    for path in paths:
        saved_rows = read_results(path)
        if speed_label == "WPM" and any(not row.get("language") for row in saved_rows):
            if analysis is None:
                from .mistake_analysis import load_analysis
                analysis = load_analysis()
            saved_rows = recover_languages(path, saved_rows, analysis)
        for row in saved_rows:
            training = row.get("is_training_run", "").lower() in ("1", "true", "yes", "y")
            if not app._should_include_training_entry(training):
                continue
            try:
                speed = float(next(row[k] for k in ("wpm", "letters_per_minute", "specials_per_minute", "symbols_per_minute", "digits_per_minute") if k in row))
                when = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError, StopIteration, KeyError):
                continue
            if math.isfinite(speed) and speed >= 0:
                rows.append((when, speed, row))
    rows.sort(key=lambda item: item[0])
    if not rows:
        return []
    figures = []
    latest_when, latest_speed, latest_row = rows[-1]

    def highlight(ax, x, y):
        ax.scatter([x], [y], s=55, color="red", edgecolors="white",
                   linewidths=0.7, zorder=5, label="Latest session")

    def page(title, note):
        fig = Figure(figsize=(10, 4.5), layout="constrained")
        ax = fig.subplots()
        ax.set_title(title)
        ax.set_ylabel(speed_label)
        fig.supxlabel(textwrap.fill(note, width=62), fontsize=9)
        figures.append(fig)
        return ax

    ax = page("Performance trend", "Dashed line: linear fit to recorded sessions; it does not establish a cause.")
    # Matplotlib date numbers preserve elapsed time, including practice gaps.
    from matplotlib.dates import date2num, AutoDateLocator, ConciseDateFormatter
    x = date2num([r[0] for r in rows])
    y = [r[1] for r in rows]
    ax.scatter(x, y, s=18, label="Recorded session")
    highlight(ax, x[-1], y[-1])
    trend(ax, x, y)
    ax.legend()
    locator = AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(ConciseDateFormatter(locator))
    ax.set_xlabel("Session date")

    # Error rates have different meanings in standard and blind mode. Keep the
    # recorded metric's name rather than combining the two definitions.
    for column, title in (("error_percentage", "Cumulative error percentage trend"),
                          ("end_error_percentage", "Final error percentage trend"),
                          ("correct_characters", "Correct characters trend"),
                          ("correct_letters", "Correct letters trend"),
                          ("correct_symbols", "Correct symbols trend"),
                          ("correct_digits", "Correct digits trend")):
        observations = []
        for when, _, row in rows:
            try:
                value = float(row.get(column, ""))
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and value >= 0:
                observations.append((date2num(when), value))
        if not observations:
            continue
        ax = page(title, "Trend uses recorded observations; days without practice are excluded.")
        ax.set_ylabel("Error (%)" if "error" in column else "Correct characters")
        x, y = zip(*observations)
        ax.scatter(x, y, s=18)
        try:
            latest_value = float(latest_row.get(column, ""))
            if math.isfinite(latest_value) and latest_value >= 0:
                highlight(ax, date2num(latest_when), latest_value)
        except (TypeError, ValueError):
            pass
        trend(ax, x, y)
        ax.legend()
        locator = AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(ConciseDateFormatter(locator))
        ax.set_xlabel("Session date")

    if speed_label != "WPM":
        return figures
    known = [r for r in rows if r[2].get("text_id")]
    note = (f"Text context recorded for {len(known)} of {len(rows)} sessions. "
            "Older results have unknown context.")
    language_known = sum(bool(row.get("language")) for _, _, row in rows)
    recovered = sum(row.get("_language_source") == "mistake analysis" for _, _, row in rows)
    language_note = (f"Language available for {language_known} of {len(rows)} sessions; "
                     f"{recovered} recovered from uniquely matching mistake-analysis records. "
                     "Unmatched older sessions remain Unknown. Single or constant groups appear as points.")
    ax = page("Performance by text language", language_note)
    languages = sorted({r[2].get("language") or "Unknown" for r in rows})
    groups = [[r[1] for r in rows if (r[2].get("language") or "Unknown") == language] for language in languages]
    language_violins(ax, groups, [f"{language}\n(n={len(group)})" for language, group in zip(languages, groups)])
    latest_language = latest_row.get("language") or "Unknown"
    highlight(ax, languages.index(latest_language) + 1, latest_speed)
    ax.legend()
    ax.set_xlabel("Text language")
    for column, title, label in (
        ("previous_completions", "Performance by previous text completions", "Previous completed runs of this exact text"),
        ("text_characters", "Performance by text length", "Characters in the full target text (including whitespace)"),
    ):
        ax = page(title, note + " Counts span practice modes and include training runs.")
        values = []
        for _, speed, row in known:
            try:
                value = int(row.get(column, ""))
            except (ValueError, TypeError):
                continue
            if value >= 0:
                values.append((value, speed))
        if values:
            x, y = zip(*values)
            ax.scatter(x, y, s=22, alpha=.7)
            try:
                latest_value = int(latest_row.get(column, ""))
                if latest_row.get("text_id") and latest_value >= 0:
                    highlight(ax, latest_value, latest_speed)
            except (TypeError, ValueError):
                pass
            trend(ax, x, y)
            if ax.get_legend_handles_labels()[0]:
                ax.legend()
        else:
            ax.text(.5, .5, "No text context recorded yet. Complete a typing session to populate this chart.",
                    ha="center", va="center", wrap=True, transform=ax.transAxes)
        ax.set_xlabel(textwrap.fill(label, width=48))
    return figures


def mark_latest_main_figure(fig, path, app):
    """Add the latest individual run to charts whose data can represent it."""
    rows = []
    speed_columns = ("wpm", "letters_per_minute", "specials_per_minute", "symbols_per_minute", "digits_per_minute")
    for row in read_results(path):
        training = str(row.get("is_training_run", "")).lower() in ("1", "true", "yes", "y")
        if not app._should_include_training_entry(training):
            continue
        try:
            when = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
            speed = float(next(row[column] for column in speed_columns if column in row))
        except (KeyError, ValueError, TypeError, StopIteration):
            continue
        if math.isfinite(speed):
            rows.append((when, speed, row))
    if not rows:
        return
    when, speed, row = max(enumerate(rows), key=lambda item: (item[1][0], item[0]))[1]
    metric = None
    for column in ("error_percentage", "end_error_percentage", "correct_characters", "correct_letters", "correct_symbols", "correct_digits"):
        try:
            value = float(row.get(column, ""))
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            metric = value
            break
    try:
        duration = float(row.get("duration_seconds", "")) / 60
        if not math.isfinite(duration):
            duration = None
    except (TypeError, ValueError):
        duration = None

    distributions = [ax for ax in fig.axes if ax.get_title().lower().endswith(" distribution")]
    for axis, value in zip(distributions[:2], (speed, metric)):
        if value is not None:
            axis.axvline(value, color="red", linestyle="--", linewidth=1.6, label="Latest session")
            app._style_legend(axis.legend(fontsize=8), app._get_plot_palette())
    for axis in fig.axes:
        if axis.get_title().lower().startswith("joint ") and metric is not None:
            axis.scatter([speed], [metric], color="red", edgecolors="white", s=55, zorder=5, label="Latest session")
            app._style_legend(axis.legend(fontsize=8), app._get_plot_palette())
        if not axis.get_title().startswith("Daily averages"):
            continue
        date_label = when.strftime("%Y-%m-%d")
        positions = {tick.get_text(): position for tick, position in zip(axis.get_xticklabels(), axis.get_xticks())}
        if date_label not in positions:
            continue
        siblings = axis.get_shared_x_axes().get_siblings(axis)
        for sibling in siblings:
            if not getattr(sibling, "_metric_color", None) or not sibling.lines:
                continue
            series_label = sibling.lines[0].get_label().lower()
            value = duration if "time" in series_label else metric if ("error" in series_label or "correct" in series_label) else speed
            if value is not None:
                sibling.scatter([positions[date_label]], [value], color="red", edgecolors="white", s=45,
                                zorder=5, label="Latest session (individual)")
        handles, labels, seen = [], [], set()
        for sibling in siblings:
            for handle, label in zip(*sibling.get_legend_handles_labels()):
                if label not in seen:
                    handles.append(handle)
                    labels.append(label)
                    seen.add(label)
        if handles:
            app._style_legend(axis.legend(handles=handles, labels=labels, fontsize=8), app._get_plot_palette())


def add_chapter_dividers(fig, start, palette):
    """Draw chapter rules in the figure so they also appear in PDF exports."""
    groups = {}
    for ax in fig.axes:
        spec = ax.get_subplotspec()
        if spec is None or not ax.get_title():
            continue
        spec = spec.get_topmost_subplotspec()
        groups.setdefault(spec.rowspan.start, []).append((ax, spec))
    multiple = len(groups) > 1
    headings = (["Distributions", "Performance relationship", "Daily performance", "Practice time"]
                if len(groups) == 4 else ["Activity calendar", "Practice time", "Practice breakdown"])
    chapters = []
    previous_bottom = 1.0
    for index, (_, members) in enumerate(sorted(groups.items())):
        ax, spec = members[0]
        box = spec.get_position(fig)
        title = headings[index] if multiple else ax.get_title()
        y = min(.98, (previous_bottom + box.y1) / 2) if multiple else .995
        line = Line2D([.03, .97], [y, y], transform=fig.transFigure,
                      color=palette["spine_color"], linewidth=1.8)
        line.set_gid("chapter-divider")
        fig.add_artist(line)
        if multiple:
            fig.text(.035, y + .004, f"Chapter {start + index} · {title}",
                     fontsize=11, weight="bold", va="bottom", color=palette["text_color"])
        chapters.append((f"{start + index}. {title}", y))
        previous_bottom = box.y0
    return chapters


class StatisticsReport:
    """A document-style viewer with a clickable table of contents."""

    def __init__(self, app, figure, extra_figures, title):
        self.window = tk.Toplevel(app.master)
        self.window.title(title)
        self.window.geometry("1200x800")
        self.window.minsize(760, 480)
        self.figures = [figure, *extra_figures]
        self.canvases = []
        self.chapters = []
        self._figure_text = {}
        sidebar = ttk.Frame(self.window, padding=10)
        sidebar.pack(side="left", fill="y")
        ttk.Label(sidebar, text="Contents", font=app.ui_font).pack(anchor="w", pady=(0, 10))
        ttk.Button(sidebar, text="Export PDF…", command=self.export_pdf).pack(anchor="w", pady=(0, 10))
        self.scroll = tk.Canvas(self.window, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.window, command=self.scroll.yview)
        scrollbar.pack(side="right", fill="y")
        self.scroll.pack(side="right", fill="both", expand=True)
        self.scroll.configure(yscrollcommand=scrollbar.set)
        self.document = ttk.Frame(self.scroll)
        content = self.scroll.create_window((0, 0), window=self.document, anchor="nw")
        self.scroll.bind("<Configure>", lambda e: self.scroll.itemconfigure(content, width=e.width))
        ttk.Label(self.document, text=f"{title} · {app.stats_filter_var.get()}",
                  font=app.ui_font, wraplength=550).pack(anchor="w", padx=16, pady=(12, 0))
        self.document.bind("<Configure>", lambda e: self.scroll.configure(scrollregion=self.scroll.bbox("all")))
        palette = app._get_plot_palette()
        self.scroll.configure(bg=palette["figure_facecolor"])
        for fig in self.figures:
            app._apply_plot_theme(fig, palette)
            chapters = add_chapter_dividers(fig, len(self.chapters) + 1, palette)
            self.chapters.extend(chapters)
            ttk.Separator(self.document, orient="horizontal").pack(fill="x", padx=8, pady=(14, 0))
            if len(chapters) == 1:
                ttk.Label(self.document, text=chapters[0][0], font=app.ui_font).pack(anchor="w", padx=16, pady=(8, 0))
            frame = ttk.Frame(self.document, padding=(8, 14))
            frame.pack(fill="x")
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            widget = canvas.get_tk_widget()
            widget.pack(fill="x")
            self.canvases.append(canvas)
            for chapter, y in chapters:
                ttk.Button(sidebar, text=chapter,
                           command=lambda w=widget, y=y: self.jump(w, chapter_y=y)).pack(fill="x", pady=2)
            for target in (widget, frame):
                target.bind("<MouseWheel>", self.wheel)
                target.bind("<Button-4>", lambda e: self.scroll.yview_scroll(-3, "units"))
                target.bind("<Button-5>", lambda e: self.scroll.yview_scroll(3, "units"))
        self.scroll.bind("<MouseWheel>", self.wheel)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

    def translate_figures(self, language):
        from matplotlib.text import Text
        for canvas in self.canvases:
            changed = False
            for label in canvas.figure.findobj(match=Text):
                current = label.get_text()
                if not current:
                    continue
                original = self._figure_text.get(id(label))
                if original is None or current not in (original, translate(original, "de")):
                    original = current
                    self._figure_text[id(label)] = original
                translated = translate(original, language)
                if translated != current:
                    label.set_text(translated)
                    changed = True
            if changed:
                canvas.draw()

    def jump(self, widget, ax=None, chapter_y=None):
        self.window.update_idletasks()
        top = widget.winfo_rooty() - self.document.winfo_rooty()
        y = chapter_y if chapter_y is not None else ax.get_position().y1
        offset = max(0, (1 - y) * widget.winfo_height() - 38)
        self.scroll.yview_moveto((top + offset) / max(1, self.document.winfo_height()))

    def wheel(self, event):
        self.scroll.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def export_pdf(self):
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension=".pdf", filetypes=[("PDF document", "*.pdf")])
        if path:
            try:
                with PdfPages(path) as pdf:
                    for figure in self.figures:
                        pdf.savefig(figure, bbox_inches="tight")
            except OSError as error:
                messagebox.showerror("Cannot export report", str(error), parent=self.window)

    def close(self):
        for canvas in self.canvases:
            canvas.figure.clear()
        self.window.destroy()
