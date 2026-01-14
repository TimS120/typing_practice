
"""Plotting helpers for the typing trainer UI."""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Any, List

import tkinter as tk
from tkinter import messagebox

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.widgets import Button
import numpy as np

from .backend import parse_training_flag
from .io_utils import (
    BLIND_LETTER_STATS_FILE_HEADER,
    BLIND_LETTER_STATS_FILE_NAME,
    BLIND_NUMBER_STATS_FILE_HEADER,
    BLIND_NUMBER_STATS_FILE_NAME,
    BLIND_SPECIAL_STATS_FILE_HEADER,
    BLIND_SPECIAL_STATS_FILE_NAME,
    BLIND_TYPING_STATS_FILE_HEADER,
    BLIND_TYPING_STATS_FILE_NAME,
    LETTER_STATS_FILE_HEADER,
    LETTER_STATS_FILE_NAME,
    NUMBER_STATS_FILE_HEADER,
    NUMBER_STATS_FILE_NAME,
    SPECIAL_STATS_FILE_HEADER,
    SPECIAL_STATS_FILE_NAME,
    STATS_FILE_HEADER,
    STATS_FILE_NAME,
    SUDDEN_DEATH_LETTER_STATS_FILE_HEADER,
    SUDDEN_DEATH_LETTER_STATS_FILE_NAME,
    SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER,
    SUDDEN_DEATH_NUMBER_STATS_FILE_NAME,
    SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER,
    SUDDEN_DEATH_SPECIAL_STATS_FILE_NAME,
    SUDDEN_DEATH_TYPING_STATS_FILE_HEADER,
    SUDDEN_DEATH_TYPING_STATS_FILE_NAME,
    TRAINING_FLAG_COLUMN,
    ensure_stats_file_header,
)


class PlotMixin:
    """Shared plotting helpers for TypingTrainerApp."""

    PLOT_LIGHT_THEME = {
        "figure_facecolor": "#f5f5f5",
        "axes_facecolor": "#ffffff",
        "text_color": "#111111",
        "spine_color": "#cbcbcb",
        "grid_color": "#d8d8d8",
        "hist_speed_color": "#3a7afe",
        "hist_error_color": "#f59542",
        "hist_correct_color": "#2ca58d",
        "bar3d_color": "#4f6d7a",
        "daily_speed_color": "#3a7afe",
        "daily_error_color": "#f79646",
        "daily_duration_color": "#2ca58d",
        "time_per_day_bar_color": "#7fb3d5",
        "time_cumulative_line_color": "#0d3b66",
        "heatmap_low_color": "#ffffff",
        "heatmap_high_color": "#0d3b66",
        "heatmap_bad_color": "#f0f0f0",
        "annotation_face_color": "#ffffff",
        "annotation_edge_color": "#333333",
        "annotation_text_color": "#111111",
        "toolbar_background": "#e9e9e9",
        "toolbar_button_background": "#d6d6d6",
        "toolbar_button_active": "#c2c2c2",
        "pie_mode_colors": ["#4f6d7a", "#7b8c5f", "#b7a57a", "#9a8c98"],
        "pie_training_colors": ["#547c8c", "#a0606a"],
        "legend_facecolor": "#ffffff",
        "legend_edgecolor": "#cbcbcb"
    }

    PLOT_DARK_THEME = {
        "figure_facecolor": "#0f1115",
        "axes_facecolor": "#181b21",
        "text_color": "#f5f5f5",
        "spine_color": "#464a52",
        "grid_color": "#30343c",
        "hist_speed_color": "#64b5f6",
        "hist_error_color": "#ffb74d",
        "hist_correct_color": "#81c784",
        "bar3d_color": "#5dade2",
        "daily_speed_color": "#64b5f6",
        "daily_error_color": "#ffb74d",
        "daily_duration_color": "#81c784",
        "time_per_day_bar_color": "#4f7cac",
        "time_cumulative_line_color": "#ffd166",
        "heatmap_low_color": "#121418",
        "heatmap_high_color": "#26c6da",
        "heatmap_bad_color": "#1b1f26",
        "annotation_face_color": "#1f232a",
        "annotation_edge_color": "#f5f5f5",
        "annotation_text_color": "#f5f5f5",
        "toolbar_background": "#1b1f26",
        "toolbar_button_background": "#2c313c",
        "toolbar_button_active": "#394152",
        "pie_mode_colors": ["#64b5f6", "#81c784", "#ffd166", "#f28e85"],
        "pie_training_colors": ["#26c6da", "#b39ddb"],
        "legend_facecolor": "#1f232a",
        "legend_edgecolor": "#555555"
    }

    def _get_plot_palette(self) -> dict[str, Any]:
        """
        Return the Matplotlib palette for the currently selected theme.
        """
        return (
            self.PLOT_DARK_THEME
            if self.dark_mode_enabled
            else self.PLOT_LIGHT_THEME
        )

    def _apply_plot_theme(
        self,
        fig: plt.Figure,
        palette: dict[str, Any]
    ) -> None:
        """
        Apply the palette colors to figure, axes, ticks, and labels.
        """
        text_color = palette["text_color"]
        fig.patch.set_facecolor(palette["figure_facecolor"])
        for ax in fig.axes:
            try:
                ax.set_facecolor(palette["axes_facecolor"])
            except Exception:
                pass
            ax.tick_params(colors=text_color)
            if hasattr(ax, "xaxis"):
                ax.xaxis.label.set_color(text_color)
            if hasattr(ax, "yaxis"):
                ax.yaxis.label.set_color(text_color)
            if hasattr(ax, "zaxis"):
                ax.zaxis.label.set_color(text_color)
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_color(text_color)
            if hasattr(ax, "get_zticklabels"):
                for label in ax.get_zticklabels():
                    label.set_color(text_color)
            if hasattr(ax, "title"):
                ax.title.set_color(text_color)
            if hasattr(ax, "spines"):
                for spine in ax.spines.values():
                    spine.set_color(palette["spine_color"])
            grid_lines = getattr(ax, "get_xgridlines", lambda: [])()
            grid_lines += getattr(ax, "get_ygridlines", lambda: [])()
            for line in grid_lines:
                line.set_color(palette["grid_color"])
        self._style_matplotlib_toolbar(fig, palette)

    def _set_widget_colors(
        self,
        widget: tk.Misc | None,
        *,
        background: str,
        foreground: str,
        active_background: str | None = None
    ) -> None:
        """
        Best-effort theming for Tk widgets that may be part of Matplotlib toolbars.
        """
        if widget is None:
            return
        for option in ("background", "bg"):
            try:
                widget.configure(**{option: background})
                break
            except tk.TclError:
                continue
        for option in ("foreground", "fg"):
            try:
                widget.configure(**{option: foreground})
                break
            except tk.TclError:
                continue
        if active_background is not None:
            try:
                widget.configure(activebackground=active_background)
            except tk.TclError:
                pass
            try:
                widget.configure(activeforeground=foreground)
            except tk.TclError:
                pass

    def _style_matplotlib_toolbar(
        self,
        fig: plt.Figure,
        palette: dict[str, Any]
    ) -> None:
        """
        Apply theme colors to the Matplotlib toolbar and its containing window.
        """
        manager = getattr(fig.canvas, "manager", None)
        if manager is None:
            return
        toolbar = getattr(manager, "toolbar", None)
        if toolbar is not None:
            self._set_widget_colors(
                toolbar,
                background=palette["toolbar_background"],
                foreground=palette["text_color"]
            )
            for child in toolbar.winfo_children():
                self._set_widget_colors(
                    child,
                    background=palette["toolbar_button_background"],
                    foreground=palette["text_color"],
                    active_background=palette["toolbar_button_active"]
                )
            message_label = getattr(toolbar, "_message_label", None)
            self._set_widget_colors(
                message_label,
                background=palette["toolbar_background"],
                foreground=palette["text_color"]
            )
        window = getattr(manager, "window", None)
        if window is not None:
            self._set_native_title_bar_theme(
                window,
                self.dark_mode_enabled,
                {
                    "titlebar_color": palette["axes_facecolor"],
                    "titlebar_text": palette["text_color"],
                    "titlebar_border": palette["spine_color"]
                }
            )

    def _style_legend(self, legend, palette: dict[str, Any]) -> None:
        """
        Apply theme colors to a legend if it exists.
        """
        if legend is None:
            return
        frame = legend.get_frame()
        if frame is not None:
            frame.set_facecolor(palette["legend_facecolor"])
            frame.set_edgecolor(palette["legend_edgecolor"])
        for text in legend.get_texts():
            text.set_color(palette["text_color"])

    def _configure_figure_window(self, fig: plt.Figure) -> None:
        """
        Center a Matplotlib figure and limit its window size to 80% of screen.
        """
        manager = getattr(fig.canvas, "manager", None)
        if manager is None:
            return
        window = getattr(manager, "window", None)
        if window is None:
            return

        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        if screen_width <= 0 or screen_height <= 0:
            return

        target_width = int(screen_width * 0.8)
        target_height = int(screen_height * 0.8)

        pos_x = int((screen_width - target_width) / 2)
        pos_y = int((screen_height - target_height) / 2)

        try:
            window.wm_geometry(f"{target_width}x{target_height}+{pos_x}+{pos_y}")
        except Exception:
            pass

    def _draw_joint_heatmap(
        self,
        *,
        fig: plt.Figure,
        ax: plt.Axes,
        x_values: list[float],
        y_values: list[float],
        x_label: str,
        y_label: str,
        title: str,
        palette: dict[str, Any]
    ) -> None:
        """
        Draw a square joint heatmap with a shared bin count on both axes.
        """
        ax.set_title(title)
        if not x_values or not y_values:
            ax.text(
                0.5,
                0.5,
                "No combined data available",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color=palette["text_color"]
            )
            ax.set_xticks([])
            ax.set_yticks([])
            return

        x_arr = np.asarray(x_values, dtype=float)
        y_arr = np.asarray(y_values, dtype=float)
        valid = np.isfinite(x_arr) & np.isfinite(y_arr)
        x_arr = x_arr[valid]
        y_arr = y_arr[valid]
        if x_arr.size == 0 or y_arr.size == 0:
            ax.text(
                0.5,
                0.5,
                "No combined data available",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color=palette["text_color"]
            )
            ax.set_xticks([])
            ax.set_yticks([])
            return

        x_edges = np.histogram_bin_edges(x_arr, bins="auto")
        y_edges = np.histogram_bin_edges(y_arr, bins="auto")
        bin_count = int(max(len(x_edges), len(y_edges)) - 1)
        if bin_count < 1:
            bin_count = 1

        x_min = float(np.nanmin(x_arr))
        x_max = float(np.nanmax(x_arr))
        y_min = float(np.nanmin(y_arr))
        y_max = float(np.nanmax(y_arr))
        if x_min == x_max:
            x_min -= 1.0
            x_max += 1.0
        if y_min == y_max:
            y_min -= 1.0
            y_max += 1.0

        xedges = np.linspace(x_min, x_max, bin_count + 1)
        yedges = np.linspace(y_min, y_max, bin_count + 1)
        hist, xedges, yedges = np.histogram2d(
            x_arr,
            y_arr,
            bins=[xedges, yedges]
        )
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "joint_heatmap",
            [
                palette["heatmap_low_color"],
                palette["heatmap_high_color"]
            ]
        )
        im = ax.pcolormesh(
            xedges,
            yedges,
            hist.T,
            cmap=cmap,
            shading="auto"
        )
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.margins(0)
        try:
            ax.set_box_aspect(1)
        except AttributeError:
            pass
        colorbar = fig.colorbar(im, ax=ax, pad=0.02)
        colorbar.set_label("Count")
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

    def _show_sudden_death_stats(
        self,
        *,
        file_path: Path,
        header: str,
        mode_label: str,
        speed_label: str,
        speed_short_label: str,
        correct_label: str
    ) -> None:
        """
        Shared visualization helper for sudden death statistics across modes.
        """
        title = f"Sudden death {mode_label} statistics"
        if not file_path.exists():
            messagebox.showinfo(
                title,
                f"No sudden death {mode_label} statistics available yet. "
                "Finish at least one sudden death run."
            )
            return

        ensure_stats_file_header(
            file_path,
            header,
            create_if_missing=False
        )

        speed_values: List[float] = []
        correct_counts: List[float] = []
        daily_stats: dict = {}

        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 6:
                    continue
                is_training_run = parse_training_flag(parts, 5)
                if not self._should_include_training_entry(is_training_run):
                    continue
                try:
                    speed_val = float(parts[1])
                    correct_val = float(parts[2])
                except ValueError:
                    continue
                try:
                    day = datetime.strptime(
                        parts[0],
                        "%Y-%m-%d %H:%M:%S"
                    ).date()
                except ValueError:
                    day = None
                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None

                speed_values.append(speed_val)
                correct_counts.append(correct_val)
                if day is not None:
                    entry = daily_stats.setdefault(
                        day,
                        {
                            "speed_sum": 0.0,
                            "speed_count": 0,
                            "correct_sum": 0.0,
                            "correct_count": 0,
                            "duration_sum": 0.0,
                        }
                    )
                    entry["speed_sum"] += speed_val
                    entry["speed_count"] += 1
                    entry["correct_sum"] += correct_val
                    entry["correct_count"] += 1
                    if duration_val is not None:
                        entry["duration_sum"] += max(duration_val, 0.0)

        if not speed_values:
            messagebox.showinfo(
                title,
                "No statistics available for the current filter selection."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_correct: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_speed.append(stats["speed_sum"] / stats["speed_count"])
                    daily_correct.append(
                        stats["correct_sum"] / stats["correct_count"]
                    )
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_speed.append(0.0)
                    daily_correct.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_correct = fig.add_subplot(grid_spec[0, 1])
        ax_joint = fig.add_subplot(grid_spec[1, :])
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_speed.hist(
            speed_values,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_speed.set_title(f"{speed_label} distribution")
        ax_speed.set_xlabel(speed_label)
        ax_speed.set_ylabel("Frequency")

        if correct_counts:
            ax_correct.hist(
                correct_counts,
                bins="auto",
                color=palette["hist_correct_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_correct.set_title(f"{correct_label} distribution")
            ax_correct.set_xlabel(correct_label)
            ax_correct.set_ylabel("Frequency")
        else:
            ax_correct.set_title(f"{correct_label} distribution")
            ax_correct.text(
                0.5,
                0.5,
                "No data available",
                ha="center",
                va="center",
                transform=ax_correct.transAxes,
                color=palette["text_color"]
            )
            ax_correct.set_xticks([])
            ax_correct.set_yticks([])

        self._draw_joint_heatmap(
            fig=fig,
            ax=ax_joint,
            x_values=speed_values,
            y_values=correct_counts,
            x_label=speed_short_label,
            y_label=correct_label,
            title=(
                f"Joint {speed_short_label} / "
                f"{correct_label.lower()} distribution"
            ),
            palette=palette
        )

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_speed,
                width=bar_width,
                color=palette["daily_speed_color"],
                label=f"Average {speed_short_label}"
            )
            ax_time.bar(
                positions,
                daily_correct,
                width=bar_width,
                color=palette["daily_error_color"],
                label=f"Average {correct_label.lower()}"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title(
                f"Daily averages ({speed_short_label} vs {correct_label.lower()})"
            )
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title(
                f"Daily averages ({speed_short_label} vs {correct_label.lower()})"
            )
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
        ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def _show_blind_stats(
        self,
        *,
        file_path: Path,
        header: str,
        mode_label: str,
        speed_label: str,
        speed_short_label: str
    ) -> None:
        """
        Shared visualization helper for blind mode statistics across modes.
        """
        title = f"Blind {mode_label} statistics"
        if not file_path.exists():
            messagebox.showinfo(
                title,
                f"No blind {mode_label} statistics available yet. "
                "Finish at least one blind mode run."
            )
            return

        ensure_stats_file_header(
            file_path,
            header,
            create_if_missing=False
        )

        speed_values: List[float] = []
        error_rates: List[float] = []
        speed_for_3d: List[float] = []
        error_for_3d: List[float] = []
        daily_stats: dict = {}

        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) < 6:
                    continue
                is_training_run = parse_training_flag(parts, 6)
                if not self._should_include_training_entry(is_training_run):
                    continue
                try:
                    day = datetime.strptime(
                        parts[0],
                        "%Y-%m-%d %H:%M:%S"
                    ).date()
                except ValueError:
                    day = None
                try:
                    speed_val = float(parts[1])
                except ValueError:
                    continue
                speed_values.append(speed_val)

                err_val: float | None = None
                if len(parts) >= 6:
                    try:
                        err_val = float(parts[5])
                    except ValueError:
                        err_val = None
                    if err_val is not None:
                        error_rates.append(err_val)
                        speed_for_3d.append(speed_val)
                        error_for_3d.append(err_val)

                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None

                if day is not None:
                    entry = daily_stats.setdefault(
                        day,
                        {
                            "speed_sum": 0.0,
                            "speed_count": 0,
                            "error_sum": 0.0,
                            "error_count": 0,
                            "duration_sum": 0.0,
                        }
                    )
                    entry["speed_sum"] += speed_val
                    entry["speed_count"] += 1
                    if err_val is not None:
                        entry["error_sum"] += err_val
                        entry["error_count"] += 1
                    if duration_val is not None:
                        entry["duration_sum"] += max(duration_val, 0.0)

        if not speed_values:
            messagebox.showinfo(
                title,
                "No statistics available for the current filter selection."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_error: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_speed.append(stats["speed_sum"] / stats["speed_count"])
                    if stats["error_count"] > 0:
                        daily_error.append(
                            stats["error_sum"] / stats["error_count"]
                        )
                    else:
                        daily_error.append(0.0)
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_speed.append(0.0)
                    daily_error.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_joint = fig.add_subplot(grid_spec[1, :])
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_speed.hist(
            speed_values,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_speed.set_title(f"{speed_label} distribution")
        ax_speed.set_xlabel(speed_label)
        ax_speed.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(
                error_rates,
                bins="auto",
                color=palette["hist_error_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_error.set_title("End error percentage distribution")
            ax_error.set_xlabel("End error percentage (%)")
            ax_error.set_ylabel("Frequency")
        else:
            ax_error.set_title("End error percentage distribution")
            ax_error.text(
                0.5,
                0.5,
                "No end error data available",
                ha="center",
                va="center",
                transform=ax_error.transAxes,
                color=palette["text_color"]
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        self._draw_joint_heatmap(
            fig=fig,
            ax=ax_joint,
            x_values=speed_for_3d,
            y_values=error_for_3d,
            x_label=speed_short_label,
            y_label="End error percentage (%)",
            title=f"Joint {speed_short_label} / end error distribution",
            palette=palette
        )

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_speed,
                width=bar_width,
                color=palette["daily_speed_color"],
                label=f"Average {speed_short_label}"
            )
            ax_time.bar(
                positions,
                daily_error,
                width=bar_width,
                color=palette["daily_error_color"],
                label="Average end error %"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title(
                f"Daily averages ({speed_short_label} vs end error %)"
            )
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            cumulative_total = 0.0
            for minutes in daily_duration_minutes:
                cumulative_total += minutes
                cumulative_duration_minutes.append(cumulative_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.6,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                linewidth=1.8,
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Time per day (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left",
                frameon=False
            )
            self._style_legend(legend, palette)
        else:
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_stats(self) -> None:
        """
        Show histograms of WPM, error percentage, and a 2D joint heatmap
        in a single Matplotlib figure.

        If no statistics file exists or no valid values can be read, an
        information dialog is shown instead.
        """
        if self.is_blind_mode_active():
            self._show_blind_stats(
                file_path=self.blind_typing_stats_file_path,
                header=BLIND_TYPING_STATS_FILE_HEADER,
                mode_label="typing",
                speed_label="Words per minute",
                speed_short_label="WPM"
            )
            return

        if self.is_sudden_death_active():
            self._show_sudden_death_stats(
                file_path=self.sudden_death_typing_stats_file_path,
                header=SUDDEN_DEATH_TYPING_STATS_FILE_HEADER,
                mode_label="typing",
                speed_label="Words per minute",
                speed_short_label="WPM",
                correct_label="Correct characters"
            )
            return

        if not self.stats_file_path.exists():
            messagebox.showinfo(
                "Statistics",
                "No statistics file found yet. "
                "Finish at least one session."
            )
            return

        ensure_stats_file_header(
            self.stats_file_path,
            STATS_FILE_HEADER,
            create_if_missing=False
        )

        wpm_values: List[float] = []
        error_rates: List[float] = []
        wpm_for_3d: List[float] = []
        error_for_3d: List[float] = []
        daily_stats: dict = {}

        with self.stats_file_path.open("r", encoding="utf-8") as stats_file:
            for line in stats_file:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) < 2:
                    continue
                is_training_run = parse_training_flag(parts, 4)
                if not self._should_include_training_entry(is_training_run):
                    continue

                try:
                    day = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S").date()
                except ValueError:
                    day = None

                try:
                    wpm_val = float(parts[1])
                except ValueError:
                    continue
                wpm_values.append(wpm_val)

                err_val: float | None = None
                if len(parts) >= 3:
                    try:
                        err_val = float(parts[2])
                    except ValueError:
                        err_val = None
                    if err_val is not None:
                        error_rates.append(err_val)
                        wpm_for_3d.append(wpm_val)
                        error_for_3d.append(err_val)

                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None

                if day is not None:
                    entry = daily_stats.setdefault(
                        day,
                        {
                            "wpm_sum": 0.0,
                            "wpm_count": 0,
                            "error_sum": 0.0,
                            "error_count": 0,
                            "duration_sum": 0.0,
                        }
                    )
                    entry["wpm_sum"] += wpm_val
                    entry["wpm_count"] += 1
                    if err_val is not None:
                        entry["error_sum"] += err_val
                        entry["error_count"] += 1
                    if duration_val is not None:
                        entry["duration_sum"] += max(duration_val, 0.0)

        if not wpm_values:
            messagebox.showinfo(
                "Statistics",
                "No statistics available for the current filter selection.",
            )
            return

        daily_dates: List[date] = []
        daily_wpm: List[float] = []
        daily_error: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_wpm.append(stats["wpm_sum"] / stats["wpm_count"])
                    if stats["error_count"] > 0:
                        daily_error.append(
                            stats["error_sum"] / stats["error_count"]
                        )
                    else:
                        daily_error.append(0.0)
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_wpm.append(0.0)
                    daily_error.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_wpm = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_joint = fig.add_subplot(grid_spec[1, :])
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_wpm.hist(
            wpm_values,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_wpm.set_title("WPM distribution")
        ax_wpm.set_xlabel("Words per minute")
        ax_wpm.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(
                error_rates,
                bins="auto",
                color=palette["hist_error_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_error.set_title("Error percentage distribution")
            ax_error.set_xlabel("Error percentage (%)")
            ax_error.set_ylabel("Frequency")
        else:
            ax_error.set_title("Error percentage distribution")
            ax_error.text(
                0.5,
                0.5,
                "No error-rate data available",
                ha="center",
                va="center",
                transform=ax_error.transAxes,
                color=palette["text_color"]
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        self._draw_joint_heatmap(
            fig=fig,
            ax=ax_joint,
            x_values=wpm_for_3d,
            y_values=error_for_3d,
            x_label="WPM",
            y_label="Error percentage (%)",
            title="Joint WPM / error percentage distribution",
            palette=palette
        )

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_wpm,
                width=bar_width,
                color=palette["daily_speed_color"],
                label="Average WPM"
            )
            ax_time.bar(
                positions,
                daily_error,
                width=bar_width,
                color=palette["daily_error_color"],
                label="Average error %"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title("Daily averages (WPM vs error %)")
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title("Daily averages (WPM vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_letter_stats(self) -> None:
        """
        Visualize stored letter mode statistics (letters per minute and errors).
        """
        if self.is_blind_mode_active():
            self._show_blind_stats(
                file_path=self.blind_letter_stats_file_path,
                header=BLIND_LETTER_STATS_FILE_HEADER,
                mode_label="letter",
                speed_label="Letters per minute",
                speed_short_label="Letters/min"
            )
            return

        if self.is_sudden_death_active():
            self._show_sudden_death_stats(
                file_path=self.sudden_death_letter_stats_file_path,
                header=SUDDEN_DEATH_LETTER_STATS_FILE_HEADER,
                mode_label="letter",
                speed_label="Letters per minute",
                speed_short_label="Letters/min",
                correct_label="Correct letters"
            )
            return

        if not self.letter_stats_file_path.exists():
            messagebox.showinfo(
                "Letter statistics",
                "No letter statistics available yet. "
                "Finish at least one letter mode session."
            )
            return

        ensure_stats_file_header(
            self.letter_stats_file_path,
            LETTER_STATS_FILE_HEADER,
            create_if_missing=False
        )

        letters_per_minute: List[float] = []
        error_rates: List[float] = []
        daily_stats: dict = {}

        with self.letter_stats_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 3:
                    continue
                is_training_run = parse_training_flag(parts, 4)
                if not self._should_include_training_entry(is_training_run):
                    continue
                try:
                    day = datetime.strptime(
                        parts[0],
                        "%Y-%m-%d %H:%M:%S"
                    ).date()
                    lpm_val = float(parts[1])
                    err_val = float(parts[2])
                except ValueError:
                    continue
                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None
                letters_per_minute.append(lpm_val)
                error_rates.append(err_val)
                entry = daily_stats.setdefault(
                    day,
                    {
                        "speed_sum": 0.0,
                        "speed_count": 0,
                        "error_sum": 0.0,
                        "error_count": 0,
                        "duration_sum": 0.0,
                    }
                )
                entry["speed_sum"] += lpm_val
                entry["speed_count"] += 1
                entry["error_sum"] += err_val
                entry["error_count"] += 1
                if duration_val is not None:
                    entry["duration_sum"] += max(duration_val, 0.0)

        if not letters_per_minute:
            messagebox.showinfo(
                "Letter statistics",
                "No statistics available for the current filter selection."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_error: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_speed.append(stats["speed_sum"] / stats["speed_count"])
                    if stats["error_count"] > 0:
                        daily_error.append(
                            stats["error_sum"] / stats["error_count"]
                        )
                    else:
                        daily_error.append(0.0)
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_speed.append(0.0)
                    daily_error.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_joint = fig.add_subplot(grid_spec[1, :])
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_speed.hist(
            letters_per_minute,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_speed.set_title("Letters per minute distribution")
        ax_speed.set_xlabel("Letters per minute")
        ax_speed.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(
                error_rates,
                bins="auto",
                color=palette["hist_error_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_error.set_title("Error percentage distribution")
            ax_error.set_xlabel("Error percentage (%)")
            ax_error.set_ylabel("Frequency")
        else:
            ax_error.set_title("Error percentage distribution")
            ax_error.text(
                0.5,
                0.5,
                "No error data available",
                ha="center",
                va="center",
                transform=ax_error.transAxes,
                color=palette["text_color"]
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        self._draw_joint_heatmap(
            fig=fig,
            ax=ax_joint,
            x_values=letters_per_minute,
            y_values=error_rates,
            x_label="Letters per minute",
            y_label="Error percentage (%)",
            title="Joint letters/minute and error distribution",
            palette=palette
        )

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_speed,
                width=bar_width,
                color=palette["daily_speed_color"],
                label="Average letters/min"
            )
            ax_time.bar(
                positions,
                daily_error,
                width=bar_width,
                color=palette["daily_error_color"],
                label="Average error %"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title("Daily averages (letters/min vs error %)")
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title("Daily averages (letters/min vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_special_stats(self) -> None:
        """
        Visualize stored special character mode statistics.
        """
        if self.is_blind_mode_active():
            self._show_blind_stats(
                file_path=self.blind_special_stats_file_path,
                header=BLIND_SPECIAL_STATS_FILE_HEADER,
                mode_label="character",
                speed_label="Special chars per minute",
                speed_short_label="Special chars/min"
            )
            return

        if self.is_sudden_death_active():
            self._show_sudden_death_stats(
                file_path=self.sudden_death_special_stats_file_path,
                header=SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER,
                mode_label="special",
                speed_label="Special chars per minute",
                speed_short_label="Special chars/min",
                correct_label="Correct symbols"
            )
            return

        if not self.special_stats_file_path.exists():
            messagebox.showinfo(
                "Special character statistics",
                "No special character statistics available yet. "
                "Finish at least one special mode session."
            )
            return

        ensure_stats_file_header(
            self.special_stats_file_path,
            SPECIAL_STATS_FILE_HEADER,
            create_if_missing=False
        )

        symbols_per_minute: List[float] = []
        error_rates: List[float] = []
        daily_stats: dict = {}

        with self.special_stats_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 3:
                    continue
                is_training_run = parse_training_flag(parts, 4)
                if not self._should_include_training_entry(is_training_run):
                    continue
                try:
                    day = datetime.strptime(
                        parts[0],
                        "%Y-%m-%d %H:%M:%S"
                    ).date()
                    spm_val = float(parts[1])
                    err_val = float(parts[2])
                except ValueError:
                    continue
                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None
                symbols_per_minute.append(spm_val)
                error_rates.append(err_val)
                entry = daily_stats.setdefault(
                    day,
                    {
                        "speed_sum": 0.0,
                        "speed_count": 0,
                        "error_sum": 0.0,
                        "error_count": 0,
                        "duration_sum": 0.0,
                    }
                )
                entry["speed_sum"] += spm_val
                entry["speed_count"] += 1
                entry["error_sum"] += err_val
                entry["error_count"] += 1
                if duration_val is not None:
                    entry["duration_sum"] += max(duration_val, 0.0)

        if not symbols_per_minute:
            messagebox.showinfo(
                "Special character statistics",
                "No statistics available for the current filter selection."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_error: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_speed.append(stats["speed_sum"] / stats["speed_count"])
                    if stats["error_count"] > 0:
                        daily_error.append(
                            stats["error_sum"] / stats["error_count"]
                        )
                    else:
                        daily_error.append(0.0)
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_speed.append(0.0)
                    daily_error.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_joint = fig.add_subplot(grid_spec[1, :])
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_speed.hist(
            symbols_per_minute,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_speed.set_title("Special chars per minute distribution")
        ax_speed.set_xlabel("Special chars per minute")
        ax_speed.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(
                error_rates,
                bins="auto",
                color=palette["hist_error_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_error.set_title("Error percentage distribution")
            ax_error.set_xlabel("Error percentage (%)")
            ax_error.set_ylabel("Frequency")
        else:
            ax_error.set_title("Error percentage distribution")
            ax_error.text(
                0.5,
                0.5,
                "No error data available",
                ha="center",
                va="center",
                transform=ax_error.transAxes,
                color=palette["text_color"]
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        self._draw_joint_heatmap(
            fig=fig,
            ax=ax_joint,
            x_values=symbols_per_minute,
            y_values=error_rates,
            x_label="Special chars per minute",
            y_label="Error percentage (%)",
            title="Joint special chars/min and error distribution",
            palette=palette
        )

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_speed,
                width=bar_width,
                color=palette["daily_speed_color"],
                label="Average special chars/min"
            )
            ax_time.bar(
                positions,
                daily_error,
                width=bar_width,
                color=palette["daily_error_color"],
                label="Average error %"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title("Daily averages (special chars/min vs error %)")
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title("Daily averages (special chars/min vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_number_stats(self) -> None:
        """
        Visualize stored number mode statistics.
        """
        if self.is_blind_mode_active():
            self._show_blind_stats(
                file_path=self.blind_number_stats_file_path,
                header=BLIND_NUMBER_STATS_FILE_HEADER,
                mode_label="number",
                speed_label="Digits per minute",
                speed_short_label="Digits/min"
            )
            return

        if self.is_sudden_death_active():
            self._show_sudden_death_stats(
                file_path=self.sudden_death_number_stats_file_path,
                header=SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER,
                mode_label="number",
                speed_label="Digits per minute",
                speed_short_label="Digits/min",
                correct_label="Correct digits"
            )
            return

        if not self.number_stats_file_path.exists():
            messagebox.showinfo(
                "Number statistics",
                "No number statistics available yet. "
                "Finish at least one number mode session."
            )
            return

        ensure_stats_file_header(
            self.number_stats_file_path,
            NUMBER_STATS_FILE_HEADER,
            create_if_missing=False
        )

        digits_per_minute: List[float] = []
        error_rates: List[float] = []
        daily_stats: dict = {}

        with self.number_stats_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(";")
                if len(parts) < 3:
                    continue
                is_training_run = parse_training_flag(parts, 4)
                if not self._should_include_training_entry(is_training_run):
                    continue
                try:
                    day = datetime.strptime(
                        parts[0],
                        "%Y-%m-%d %H:%M:%S"
                    ).date()
                    dpm_val = float(parts[1])
                    err_val = float(parts[2])
                except ValueError:
                    continue
                duration_val: float | None = None
                if len(parts) >= 4:
                    try:
                        duration_val = float(parts[3])
                    except ValueError:
                        duration_val = None
                digits_per_minute.append(dpm_val)
                error_rates.append(err_val)
                entry = daily_stats.setdefault(
                    day,
                    {
                        "speed_sum": 0.0,
                        "speed_count": 0,
                        "error_sum": 0.0,
                        "error_count": 0,
                        "duration_sum": 0.0,
                    }
                )
                entry["speed_sum"] += dpm_val
                entry["speed_count"] += 1
                entry["error_sum"] += err_val
                entry["error_count"] += 1
                if duration_val is not None:
                    entry["duration_sum"] += max(duration_val, 0.0)

        if not digits_per_minute:
            messagebox.showinfo(
                "Number statistics",
                "No statistics available for the current filter selection."
            )
            return

        daily_dates: List[date] = []
        daily_speed: List[float] = []
        daily_error: List[float] = []
        daily_duration_minutes: List[float] = []
        if daily_stats:
            start_date = min(daily_stats)
            end_date = max(datetime.now().date(), start_date)
            current_day = start_date
            while current_day <= end_date:
                daily_dates.append(current_day)
                stats = daily_stats.get(current_day)
                if stats:
                    daily_speed.append(stats["speed_sum"] / stats["speed_count"])
                    if stats["error_count"] > 0:
                        daily_error.append(
                            stats["error_sum"] / stats["error_count"]
                        )
                    else:
                        daily_error.append(0.0)
                    daily_duration_minutes.append(
                        stats.get("duration_sum", 0.0) / 60.0
                    )
                else:
                    daily_speed.append(0.0)
                    daily_error.append(0.0)
                    daily_duration_minutes.append(0.0)
                current_day += timedelta(days=1)

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(12, 10))
        self._configure_figure_window(fig)
        grid_spec = fig.add_gridspec(4, 2, height_ratios=[1.0, 1.2, 1.0, 0.8])
        grid_spec.update(hspace=0.75, wspace=0.4)

        ax_speed = fig.add_subplot(grid_spec[0, 0])
        ax_error = fig.add_subplot(grid_spec[0, 1])
        ax_joint = fig.add_subplot(grid_spec[1, :])
        ax_time = fig.add_subplot(grid_spec[2, :])
        ax_time_spent = fig.add_subplot(grid_spec[3, :])
        ax_time_spent_right = ax_time_spent.twinx()

        ax_speed.hist(
            digits_per_minute,
            bins="auto",
            color=palette["hist_speed_color"],
            edgecolor=palette["axes_facecolor"],
            alpha=0.85
        )
        ax_speed.set_title("Digits per minute distribution")
        ax_speed.set_xlabel("Digits per minute")
        ax_speed.set_ylabel("Frequency")

        if error_rates:
            ax_error.hist(
                error_rates,
                bins="auto",
                color=palette["hist_error_color"],
                edgecolor=palette["axes_facecolor"],
                alpha=0.85
            )
            ax_error.set_title("Error percentage distribution")
            ax_error.set_xlabel("Error percentage (%)")
            ax_error.set_ylabel("Frequency")
        else:
            ax_error.set_title("Error percentage distribution")
            ax_error.text(
                0.5,
                0.5,
                "No error data available",
                ha="center",
                va="center",
                transform=ax_error.transAxes,
                color=palette["text_color"]
            )
            ax_error.set_xticks([])
            ax_error.set_yticks([])

        self._draw_joint_heatmap(
            fig=fig,
            ax=ax_joint,
            x_values=digits_per_minute,
            y_values=error_rates,
            x_label="Digits per minute",
            y_label="Error percentage (%)",
            title="Joint digits/minute and error distribution",
            palette=palette
        )

        if daily_dates:
            positions = np.arange(len(daily_dates))
            bar_width = 0.25
            ax_time.bar(
                positions - bar_width,
                daily_speed,
                width=bar_width,
                color=palette["daily_speed_color"],
                label="Average digits/min"
            )
            ax_time.bar(
                positions,
                daily_error,
                width=bar_width,
                color=palette["daily_error_color"],
                label="Average error %"
            )
            ax_time.bar(
                positions + bar_width,
                daily_duration_minutes,
                width=bar_width,
                color=palette["daily_duration_color"],
                label="Total time (min)"
            )
            formatted_days = [day.strftime("%Y-%m-%d") for day in daily_dates]
            ax_time.set_xticks(positions)
            ax_time.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time.set_ylabel("Daily averages / total time")
            ax_time.set_title("Daily averages (digits/min vs error %)")
            legend = ax_time.legend()
            self._style_legend(legend, palette)

            cumulative_duration_minutes: List[float] = []
            running_total = 0.0
            for minutes in daily_duration_minutes:
                running_total += minutes
                cumulative_duration_minutes.append(running_total)

            ax_time_spent.bar(
                positions,
                daily_duration_minutes,
                width=0.4,
                color=palette["time_per_day_bar_color"],
                label="Time per day (min)"
            )
            ax_time_spent_right.plot(
                positions,
                cumulative_duration_minutes,
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                label="Cumulative time (min)"
            )
            ax_time_spent.set_xticks(positions)
            ax_time_spent.set_xticklabels(
                formatted_days,
                rotation=45,
                ha="right"
            )
            ax_time_spent.set_ylabel("Daily time (min)")
            ax_time_spent_right.set_ylabel("Cumulative time (min)")
            ax_time_spent.set_title("Time spent per day")
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_time_spent_right.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left"
            )
            self._style_legend(legend, palette)
        else:
            ax_time.set_title("Daily averages (digits/min vs error %)")
            ax_time.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time.transAxes,
                color=palette["text_color"]
            )
            ax_time.set_xticks([])
            ax_time.set_yticks([])
            ax_time_spent.set_title("Time spent per day")
            ax_time_spent.text(
                0.5,
                0.5,
                "No dated entries available",
                ha="center",
                va="center",
                transform=ax_time_spent.transAxes,
                color=palette["text_color"]
            )
            ax_time_spent.set_xticks([])
            ax_time_spent.set_yticks([])
            ax_time_spent_right.set_yticks([])

        formatter = mticker.FormatStrFormatter("%.1f")
        ax_time_spent.yaxis.set_major_formatter(formatter)
        ax_time_spent_right.yaxis.set_major_formatter(formatter)

        self._apply_plot_theme(fig, palette)
        plt.tight_layout(pad=1.3)
        plt.show()

    def show_general_stats(self) -> None:
        """
        Display cumulative time spent across all modes with heatmap and timeline views.
        """
        def _training_flag_index_from_header(header: str) -> int | None:
            columns = header.split(";")
            try:
                return columns.index(TRAINING_FLAG_COLUMN)
            except ValueError:
                return None

        stats_sources = [
            (
                self.stats_file_path,
                STATS_FILE_HEADER,
                "typing",
                _training_flag_index_from_header(STATS_FILE_HEADER)
            ),
            (
                self.letter_stats_file_path,
                LETTER_STATS_FILE_HEADER,
                "letter",
                _training_flag_index_from_header(LETTER_STATS_FILE_HEADER)
            ),
            (
                self.special_stats_file_path,
                SPECIAL_STATS_FILE_HEADER,
                "character",
                _training_flag_index_from_header(SPECIAL_STATS_FILE_HEADER)
            ),
            (
                self.number_stats_file_path,
                NUMBER_STATS_FILE_HEADER,
                "number",
                _training_flag_index_from_header(NUMBER_STATS_FILE_HEADER)
            ),
            (
                self.sudden_death_typing_stats_file_path,
                SUDDEN_DEATH_TYPING_STATS_FILE_HEADER,
                "typing",
                _training_flag_index_from_header(
                    SUDDEN_DEATH_TYPING_STATS_FILE_HEADER
                )
            ),
            (
                self.sudden_death_letter_stats_file_path,
                SUDDEN_DEATH_LETTER_STATS_FILE_HEADER,
                "letter",
                _training_flag_index_from_header(
                    SUDDEN_DEATH_LETTER_STATS_FILE_HEADER
                )
            ),
            (
                self.sudden_death_special_stats_file_path,
                SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER,
                "character",
                _training_flag_index_from_header(
                    SUDDEN_DEATH_SPECIAL_STATS_FILE_HEADER
                )
            ),
            (
                self.sudden_death_number_stats_file_path,
                SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER,
                "number",
                _training_flag_index_from_header(
                    SUDDEN_DEATH_NUMBER_STATS_FILE_HEADER
                )
            ),
            (
                self.blind_typing_stats_file_path,
                BLIND_TYPING_STATS_FILE_HEADER,
                "typing",
                _training_flag_index_from_header(
                    BLIND_TYPING_STATS_FILE_HEADER
                )
            ),
            (
                self.blind_letter_stats_file_path,
                BLIND_LETTER_STATS_FILE_HEADER,
                "letter",
                _training_flag_index_from_header(
                    BLIND_LETTER_STATS_FILE_HEADER
                )
            ),
            (
                self.blind_special_stats_file_path,
                BLIND_SPECIAL_STATS_FILE_HEADER,
                "character",
                _training_flag_index_from_header(
                    BLIND_SPECIAL_STATS_FILE_HEADER
                )
            ),
            (
                self.blind_number_stats_file_path,
                BLIND_NUMBER_STATS_FILE_HEADER,
                "number",
                _training_flag_index_from_header(
                    BLIND_NUMBER_STATS_FILE_HEADER
                )
            )
        ]

        mode_labels: dict[str, str] = {
            "typing": "Typing text",
            "letter": "Letter mode",
            "number": "Number mode",
            "character": "Character mode"
        }

        daily_seconds: dict[date, float] = {}
        total_seconds = 0.0
        mode_seconds: dict[str, float] = {key: 0.0 for key in mode_labels}
        training_seconds = {"training": 0.0, "regular": 0.0}

        def _is_training_run(parts: list[str], flag_index: int | None) -> bool:
            if flag_index is None or flag_index >= len(parts):
                return False
            return parts[flag_index].strip().lower() in {"1", "true", "yes", "y"}

        for path, header, mode_key, training_index in stats_sources:
            if not path.exists():
                continue
            ensure_stats_file_header(
                path,
                header,
                create_if_missing=False
            )
            with path.open("r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line or line == header:
                        continue
                    parts = line.split(";")
                    if len(parts) <= 3:
                        continue
                    try:
                        timestamp = datetime.strptime(
                            parts[0],
                            "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        continue
                    try:
                        duration_seconds = float(parts[3])
                    except ValueError:
                        continue
                    duration_seconds = max(duration_seconds, 0.0)
                    if duration_seconds == 0.0:
                        continue
                    day = timestamp.date()
                    daily_seconds[day] = (
                        daily_seconds.get(day, 0.0) + duration_seconds
                    )
                    total_seconds += duration_seconds
                    mode_seconds[mode_key] += duration_seconds
                    if _is_training_run(parts, training_index):
                        training_seconds["training"] += duration_seconds
                    else:
                        training_seconds["regular"] += duration_seconds

        today = datetime.now().date()
        current_year_offset = 0

        def _first_of_month(value: date) -> date:
            return date(value.year, value.month, 1)

        today_ordinal = today.toordinal()
        min_end_ordinal = date.min.toordinal() + 364
        max_end_ordinal = date.max.toordinal()

        def _compute_year_view(year_offset: int) -> dict[str, Any]:
            target_end = today_ordinal - year_offset * 365
            target_end = max(min_end_ordinal, min(max_end_ordinal, target_end))
            window_end = date.fromordinal(target_end)
            window_start = window_end - timedelta(days=364)

            start_week_offset = window_start.weekday()
            start_week_ordinal = window_start.toordinal() - start_week_offset
            if start_week_ordinal < date.min.toordinal():
                start_week_ordinal = date.min.toordinal()
            start_week = date.fromordinal(start_week_ordinal)

            end_week_offset = 6 - window_end.weekday()
            end_week_ordinal = window_end.toordinal() + end_week_offset
            if end_week_ordinal > date.max.toordinal():
                end_week_ordinal = date.max.toordinal()
            end_week = date.fromordinal(end_week_ordinal)

            total_days = (end_week - start_week).days + 1
            num_weeks = max(total_days // 7, 1)

            heatmap_data = np.full((7, num_weeks), np.nan, dtype=float)
            date_grid: List[List[date | None]] = [
                [None for _ in range(num_weeks)] for _ in range(7)
            ]

            current_day = start_week
            for idx in range(total_days):
                week_idx = idx // 7
                weekday_idx = current_day.weekday()
                if week_idx >= num_weeks:
                    break
                date_grid[weekday_idx][week_idx] = current_day
                if window_start <= current_day <= window_end:
                    seconds = daily_seconds.get(current_day, 0.0)
                    heatmap_data[weekday_idx, week_idx] = seconds / 60.0
                current_day += timedelta(days=1)

            week_start_days = [
                start_week + timedelta(days=week_idx * 7)
                for week_idx in range(num_weeks)
            ]
            tick_positions: List[int] = []
            tick_labels: List[str] = []
            for idx, week_start in enumerate(week_start_days):
                if idx == 0 or week_start.day <= 7:
                    tick_positions.append(idx)
                    tick_labels.append(week_start.strftime("%b %d"))

            monthly_totals: dict[tuple[int, int], float] = {}
            for day_value, seconds in daily_seconds.items():
                if window_start <= day_value <= window_end:
                    key = (day_value.year, day_value.month)
                    monthly_totals[key] = (
                        monthly_totals.get(key, 0.0) + seconds / 60.0
                    )

            monthly_labels: List[str] = []
            monthly_minutes: List[float] = []
            cumulative_minutes: List[float] = []
            cumulative_total = 0.0
            current_month = _first_of_month(window_start)
            last_month = _first_of_month(window_end)
            while current_month <= last_month:
                key = (current_month.year, current_month.month)
                minutes_value = monthly_totals.get(key, 0.0)
                cumulative_total += minutes_value
                monthly_labels.append(current_month.strftime("%b %Y"))
                monthly_minutes.append(minutes_value)
                cumulative_minutes.append(cumulative_total)
                if current_month.month == 12:
                    current_month = date(current_month.year + 1, 1, 1)
                else:
                    current_month = date(
                        current_month.year,
                        current_month.month + 1,
                        1
                    )

            max_minutes = np.nanmax(heatmap_data)
            if not np.isfinite(max_minutes) or max_minutes == 0.0:
                max_minutes = 1.0

            range_label = (
                f"{window_start.strftime('%b %d, %Y')} - "
                f"{window_end.strftime('%b %d, %Y')}"
            )

            return {
                "window_start": window_start,
                "window_end": window_end,
                "heatmap_data": heatmap_data,
                "date_grid": date_grid,
                "num_weeks": num_weeks,
                "tick_positions": tick_positions,
                "tick_labels": tick_labels,
                "monthly_labels": monthly_labels,
                "monthly_minutes": monthly_minutes,
                "cumulative_minutes": cumulative_minutes,
                "max_minutes": max_minutes,
                "range_label": range_label
            }

        palette = self._get_plot_palette()
        fig = plt.figure(figsize=(14, 10.2))
        gridspec = fig.add_gridspec(
            3,
            2,
            height_ratios=(2.3, 1.15, 0.9),
            hspace=0.65,
            wspace=0.12
        )
        ax_heatmap = fig.add_subplot(gridspec[0, :])
        ax_time_spent = fig.add_subplot(gridspec[1, :])
        ax_modes = fig.add_subplot(gridspec[2, 0])
        ax_training = fig.add_subplot(gridspec[2, 1])
        ax_cumulative = ax_time_spent.twinx()
        self._configure_figure_window(fig)
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "time_heatmap",
            [
                palette["heatmap_low_color"],
                palette["heatmap_high_color"]
            ]
        )
        cmap.set_bad(color=palette["heatmap_bad_color"])
        y_formatter = mticker.FormatStrFormatter("%.0f")

        button_prev_ax = fig.add_axes([0.87, 0.74, 0.11, 0.05])
        button_next_ax = fig.add_axes([0.87, 0.66, 0.11, 0.05])
        button_prev_ax.set_in_layout(False)
        button_next_ax.set_in_layout(False)
        button_prev = Button(button_prev_ax, "Previous year")
        button_next = Button(button_next_ax, "Next year")
        button_prev.color = palette["toolbar_background"]
        button_next.color = palette["toolbar_background"]
        button_prev.hovercolor = palette["toolbar_button_active"]
        button_next.hovercolor = palette["toolbar_button_active"]

        weekday_labels = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday"
        ]

        heatmap_state: dict[str, Any] = {
            "heatmap_data": None,
            "date_grid": [],
            "num_weeks": 0,
            "annotation": None
        }
        colorbar = None

        def _style_year_buttons() -> None:
            button_prev.ax.set_facecolor(palette["toolbar_background"])
            button_next.ax.set_facecolor(palette["toolbar_background"])
            button_prev.label.set_color(palette["text_color"])
            button_next.label.set_color(palette["text_color"])

        _style_year_buttons()

        def _format_minutes(value: float) -> str:
            if value >= 60.0:
                return f"{value / 60.0:.1f} h"
            return f"{value:.1f} min"

        def _draw_year_view(year_offset: int) -> None:
            nonlocal colorbar
            view_data = _compute_year_view(year_offset)
            ax_heatmap.clear()
            norm = mcolors.Normalize(
                vmin=0.0,
                vmax=view_data["max_minutes"]
            )
            im = ax_heatmap.imshow(
                view_data["heatmap_data"],
                aspect="auto",
                origin="upper",
                cmap=cmap,
                norm=norm
            )
            if colorbar is None:
                colorbar = fig.colorbar(im, ax=ax_heatmap, pad=0.02)
            else:
                colorbar.update_normal(im)
            colorbar.set_label("Minutes spent per day")
            ax_heatmap.set_yticks(range(7))
            ax_heatmap.set_yticklabels(weekday_labels)
            if view_data["tick_positions"]:
                ax_heatmap.set_xticks(view_data["tick_positions"])
                ax_heatmap.set_xticklabels(
                    view_data["tick_labels"],
                    rotation=45,
                    ha="right"
                )
            else:
                ax_heatmap.set_xticks([])
                ax_heatmap.set_xticklabels([])
            ax_heatmap.set_xlabel("Weeks (starting Mondays)")
            ax_heatmap.set_ylabel("Day of week")
            ax_heatmap.set_title(
                f"Daily time spent ({view_data['range_label']})"
            )
            annotation = ax_heatmap.annotate(
                "",
                xy=(0, 0),
                xytext=(15, 15),
                textcoords="offset points",
                bbox=dict(
                    boxstyle="round",
                    fc=palette["annotation_face_color"],
                    ec=palette["annotation_edge_color"],
                    alpha=0.9
                ),
                arrowprops=dict(
                    arrowstyle="->",
                    color=palette["annotation_edge_color"]
                ),
                color=palette["annotation_text_color"]
            )
            annotation.set_visible(False)

            heatmap_state["heatmap_data"] = view_data["heatmap_data"]
            heatmap_state["date_grid"] = view_data["date_grid"]
            heatmap_state["num_weeks"] = view_data["num_weeks"]
            heatmap_state["annotation"] = annotation

            ax_time_spent.clear()
            ax_cumulative.clear()
            month_positions = np.arange(len(view_data["monthly_minutes"]))
            ax_time_spent.bar(
                month_positions,
                view_data["monthly_minutes"],
                width=0.5,
                color=palette["time_per_day_bar_color"],
                label="Time per month (min)"
            )
            ax_cumulative.plot(
                month_positions,
                view_data["cumulative_minutes"],
                color=palette["time_cumulative_line_color"],
                marker="o",
                markerfacecolor=palette["axes_facecolor"],
                markeredgecolor=palette["time_cumulative_line_color"],
                linewidth=1.8,
                label="Cumulative time (min)"
            )
            if len(month_positions) > 0:
                ax_time_spent.set_xticks(month_positions)
                ax_time_spent.set_xticklabels(
                    view_data["monthly_labels"],
                    rotation=45,
                    ha="right"
                )
            else:
                ax_time_spent.set_xticks([])
                ax_time_spent.set_xticklabels([])
            ax_time_spent.set_ylabel("Minutes per month")
            ax_cumulative.set_ylabel("Cumulative minutes")
            ax_time_spent.set_xlabel("Month")
            ax_time_spent.set_title(
                f"Time spent progression ({view_data['range_label']})"
            )
            ax_time_spent.yaxis.set_major_formatter(y_formatter)
            ax_cumulative.yaxis.set_major_formatter(y_formatter)
            handles, labels = ax_time_spent.get_legend_handles_labels()
            handles2, labels2 = ax_cumulative.get_legend_handles_labels()
            legend = ax_time_spent.legend(
                handles + handles2,
                labels + labels2,
                loc="upper left",
                frameon=False
            )
            self._style_legend(legend, palette)
            self._apply_plot_theme(fig, palette)
            _style_year_buttons()
            fig.canvas.draw_idle()

        def _shift_year(delta: int) -> None:
            nonlocal current_year_offset
            current_year_offset += delta
            _draw_year_view(current_year_offset)

        def _on_mouse_move(event) -> None:
            annotation = heatmap_state.get("annotation")
            heatmap_data = heatmap_state.get("heatmap_data")
            date_grid = heatmap_state.get("date_grid")
            num_weeks = heatmap_state.get("num_weeks", 0)
            if (
                event.inaxes != ax_heatmap
                or event.xdata is None
                or event.ydata is None
                or annotation is None
                or heatmap_data is None
                or not date_grid
            ):
                if annotation and annotation.get_visible():
                    annotation.set_visible(False)
                    fig.canvas.draw_idle()
                return
            week_idx = int(event.xdata)
            weekday_idx = int(event.ydata)
            if (
                week_idx < 0
                or week_idx >= num_weeks
                or weekday_idx < 0
                or weekday_idx >= 7
            ):
                if annotation.get_visible():
                    annotation.set_visible(False)
                    fig.canvas.draw_idle()
                return
            date_value = date_grid[weekday_idx][week_idx]
            cell_value = heatmap_data[weekday_idx, week_idx]
            if date_value is None or not np.isfinite(cell_value):
                if annotation.get_visible():
                    annotation.set_visible(False)
                    fig.canvas.draw_idle()
                return
            annotation.xy = (week_idx, weekday_idx)
            if week_idx >= num_weeks - 5:
                annotation.xytext = (-15, 15)
                annotation.set_ha("right")
            else:
                annotation.xytext = (15, 15)
                annotation.set_ha("left")
            annotation.set_text(
                f"{date_value.strftime('%Y-%m-%d (%a)')}\n"
                f"Time: {_format_minutes(cell_value)}"
            )
            annotation.set_visible(True)
            fig.canvas.draw_idle()

        def _build_pie_chart(
            ax: plt.Axes,
            values: list[float],
            label_texts: list[str],
            colors: list[str],
            title: str
        ) -> None:
            ax.clear()
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            total = sum(values)
            if total <= 0.0:
                ax.text(
                    0.5,
                    0.5,
                    "No time recorded yet",
                    ha="center",
                    va="center",
                    color=palette["text_color"]
                )
                ax.set_title(title, pad=12)
                return
            wedges, _ = ax.pie(
                values,
                colors=colors,
                startangle=90
            )
            legend_entries = []
            for label, value in zip(label_texts, values):
                percent = (value / total * 100.0) if total else 0.0
                legend_entries.append(
                    f"{label}: {percent:.1f}% ({_format_minutes(value)})"
                )
            legend = ax.legend(
                wedges,
                legend_entries,
                loc="center left",
                bbox_to_anchor=(0.9, 0.5),
                frameon=False
            )
            self._style_legend(legend, palette)
            ax.set_title(title, pad=16)

        mode_order = ["typing", "letter", "number", "character"]
        mode_minutes = [mode_seconds[key] / 60.0 for key in mode_order]
        training_minutes = [
            training_seconds["training"] / 60.0,
            training_seconds["regular"] / 60.0
        ]

        mode_colors = palette["pie_mode_colors"]
        _build_pie_chart(
            ax_modes,
            mode_minutes,
            [mode_labels[key] for key in mode_order],
            mode_colors,
            "Time spent by mode"
        )

        training_labels = ["Training mode", "Non-training mode"]
        training_colors = palette["pie_training_colors"]
        _build_pie_chart(
            ax_training,
            training_minutes,
            training_labels,
            training_colors,
            "Training vs non-training time"
        )

        _draw_year_view(current_year_offset)
        fig.canvas.mpl_connect("motion_notify_event", _on_mouse_move)
        button_prev.on_clicked(lambda _event: _shift_year(1))
        button_next.on_clicked(lambda _event: _shift_year(-1))

        fig.subplots_adjust(top=0.94, bottom=0.02, left=0.05, right=0.82)
        plt.show()
