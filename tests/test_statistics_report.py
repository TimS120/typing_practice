"""Statistics context, legacy schema, trends, and document navigation checks."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from matplotlib.figure import Figure
import numpy as np

from utils import backend, io_utils
from utils.statistics_data import read_results, recover_languages
from utils.statistics_report import context_figures, trend, language_violins


class ResultsFixture:
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.environment = patch.object(io_utils, "get_data_dir", return_value=self.directory)
        self.environment.start()
        self.details = {"text": " exact\ttext\n ", "language": "English"}
        self.standard = io_utils.get__file_path(io_utils.STATS_FILE_NAME)
        self.sudden = io_utils.get__file_path(io_utils.SUDDEN_DEATH_TYPING_STATS_FILE_NAME)
        self.blind = io_utils.get__file_path(io_utils.BLIND_TYPING_STATS_FILE_NAME)

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()


class ContextTests(ResultsFixture, unittest.TestCase):
    def test_old_results_extend_header_once_and_keep_unknown_context(self):
        legacy = "timestamp;wpm;error_percentage;duration_seconds;is_training_run"
        io_utils.write_encrypted(self.standard, legacy + "\n2026-01-01 12:00:00;40;2;30;0\n")
        backend.save_wpm_result(self.standard, 50, 1, 30, False, text_details=self.details)
        backend.save_wpm_result(self.standard, 60, 0, 30, False, text_details=self.details)
        rows = read_results(self.standard)
        self.assertEqual(len(rows), 3)
        self.assertIsNone(rows[0]["text_id"])
        self.assertEqual(rows[0]["wpm"], "40")
        self.assertEqual([r["previous_completions"] for r in rows[1:]], ["0", "1"])
        self.assertEqual(io_utils.read_encrypted(self.standard).count("timestamp;"), 1)
        self.assertNotIn(self.details["text"].encode(), self.standard.read_bytes())

    def test_repetitions_span_modes_include_training_and_exclude_failures(self):
        backend.save_wpm_result(self.standard, 50, 0, 20, True, text_details=self.details)
        backend.save_sudden_death_wpm_result(self.sudden, 50, 3, 20, False, False, text_details=self.details)
        backend.save_blind_typing_result(self.blind, 50, 8, 20, True, 1, False, text_details=self.details)
        backend.save_sudden_death_wpm_result(self.sudden, 50, 8, 20, True, False, text_details=self.details)
        self.assertEqual(read_results(self.blind)[0]["previous_completions"], "1")
        self.assertEqual(read_results(self.sudden)[-1]["previous_completions"], "2")
        row = read_results(self.standard)[0]
        self.assertEqual(row["text_characters"], str(len(self.details["text"])))
        self.assertEqual(row["text_id"], hashlib.sha256(self.details["text"].encode()).hexdigest())
        self.assertEqual(row["language"], "English")
        backend.save_wpm_result(self.standard, 50, 0, 20, False,
                                text_details={**self.details, "text": self.details["text"] + "x"})
        self.assertEqual(read_results(self.standard)[-1]["previous_completions"], "0")

    def test_historical_language_requires_unique_exact_session_match(self):
        rows = [{"timestamp": "2026-10-26 12:00:00", "is_training_run": "0"},
                {"timestamp": "2026-10-26 12:01:00", "is_training_run": "1"},
                {"timestamp": "2026-10-26 12:02:00", "is_training_run": "0"}]
        record = {"timestamp": "2026-10-26T12:00:00.123+01:00", "mode": "typing",
                  "variant": "standard", "training": False, "outcome": "Completed", "language": "German"}
        matches = recover_languages(self.standard, rows, [record])
        self.assertEqual(matches[0]["language"], "German")
        self.assertNotIn("language", rows[0])
        self.assertNotIn("language", matches[1])
        for changed in ({"mode": "letter"}, {"variant": "blind"}, {"training": True},
                        {"outcome": "Sudden-death failure"}, {"timestamp": "2026-10-26T12:00:01+01:00"}):
            self.assertNotIn("language", recover_languages(self.standard, rows, [{**record, **changed}])[0])
        self.assertNotIn("language", recover_languages(self.standard, rows, [record, record])[0])
        self.assertNotIn("language", recover_languages(self.standard, [rows[0], rows[0]], [record])[0])
        known = [{**rows[0], "language": "English"}]
        self.assertEqual(recover_languages(self.standard, known, [record])[0]["language"], "English")

    def test_daily_series_skip_missing_days_and_have_vertical_padding(self):
        from utils.plot_utils import PlotMixin
        from datetime import date
        plotter = PlotMixin()
        ax = Figure().subplots()
        dates = [date(2026, 10, day) for day in (1, 2, 3)]
        metrics = [([40, 0, 80], "WPM"), ([0, 0, 0], "Error %"), ([1, 0, 1], "Minutes")]
        axes = plotter._plot_daily_metrics(ax, [0, 1, 2], dates, {dates[0]: {}, dates[2]: {}},
                                           metrics, plotter.PLOT_LIGHT_THEME)
        for axis, (values, _) in zip(axes, metrics):
            np.testing.assert_array_equal(axis.lines[0].get_xdata(), [0, 2])
            np.testing.assert_array_equal(axis.lines[0].get_ydata(), [values[0], values[2]])
            low, high = axis.get_ylim()
            for point in axis.lines[0].get_ydata():
                self.assertGreaterEqual((point - low) / (high - low), 0.099)
                self.assertGreaterEqual((high - point) / (high - low), 0.099)

    def test_language_violins_are_light_blue_and_handle_single_constant_groups(self):
        from matplotlib.collections import PolyCollection, PathCollection
        from matplotlib.colors import to_rgba
        ax = Figure().subplots()
        language_violins(ax, [[30, 40, 60], [50], [20, 20]], ["English", "German", "Unknown"])
        bodies = [item for item in ax.collections if isinstance(item, PolyCollection)]
        self.assertEqual(len(bodies), 1)
        np.testing.assert_allclose(bodies[0].get_facecolor()[0], to_rgba("#add8e6", 0.85))
        points = [item for item in ax.collections if isinstance(item, PathCollection)]
        self.assertEqual(len(points), 2)
        self.assertEqual([tick.get_text() for tick in ax.get_xticklabels()], ["English", "German", "Unknown"])
        ax.figure.canvas.draw()

    def test_trend_requires_distinct_finite_observations(self):
        ax = Figure().subplots()
        self.assertFalse(trend(ax, [1], [4]))
        self.assertFalse(trend(ax, [1, 1], [4, 5]))
        self.assertTrue(trend(ax, [1, 2, 3, 4], [3, 5, 7, float("nan")]))
        np.testing.assert_allclose(ax.lines[-1].get_ydata(), [3, 7])

    def test_latest_marker_uses_latest_filtered_session_and_missing_metadata(self):
        backend.save_wpm_result(self.standard, 30, 3, 20, False, text_details=self.details)
        backend.save_wpm_result(self.standard, 60, 2, 20, False, text_details=self.details)
        backend.save_wpm_result(self.standard, 99, 1, 20, True, text_details=self.details)
        app = SimpleNamespace(_should_include_training_entry=lambda training: not training)
        figures = context_figures(app, [self.standard], "WPM")
        for fig in figures:
            markers = [item for item in fig.axes[0].collections if item.get_label() == "Latest session"]
            self.assertEqual(len(markers), 1, fig.axes[0].get_title())
        self.assertEqual(float(figures[0].axes[0].collections[1].get_offsets()[0][1]), 60)
        self.assertEqual(float(figures[1].axes[0].collections[1].get_offsets()[0][1]), 2)

    def test_context_charts_follow_run_filter_and_do_not_invent_old_metadata(self):
        backend.save_wpm_result(self.standard, 50, 0, 20, False, text_details=self.details)
        backend.save_wpm_result(self.standard, 500, 0, 20, True, text_details=self.details)
        backend.save_wpm_result(self.standard, 30, 0, 20, False)
        app = SimpleNamespace(_should_include_training_entry=lambda flag: not flag)
        figures = context_figures(app, [self.standard], "WPM")
        self.assertEqual(len(figures), 5)
        self.assertEqual(len(figures[0].axes[0].collections[0].get_offsets()), 2)
        self.assertEqual(len(figures[3].axes[0].collections[0].get_offsets()), 1)
        labels = [label.get_text() for label in figures[2].axes[0].get_xticklabels()]
        self.assertIn("Unknown\n(n=1)", labels)
        self.assertIn("English\n(n=1)", labels)


@unittest.skipUnless(os.environ.get("TYPING_PRACTICE_TEST_DISPLAY") == "isolated", "Requires isolated Xvfb")
class ReportGuiTests(ResultsFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        import tkinter as tk
        from utils.ui_utils import TypingTrainerApp
        self.detector = patch.object(TypingTrainerApp, "_detect_system_dark_mode", return_value=False)
        self.detector.start()
        self.root = tk.Tk()
        self.app = TypingTrainerApp(self.root, [{"name": "Passage", **self.details}])
        self.root.update()

    def tearDown(self):
        self.app.close()
        self.detector.stop()
        super().tearDown()

    def test_document_scroll_chapters_resize_and_pdf_export(self):
        backend.save_wpm_result(self.standard, 50, 0, 20, False, text_details=self.details)
        backend.save_wpm_result(self.standard, 60, 0, 20, False, text_details=self.details)
        self.app.show_stats()
        self.root.update()
        report = self.app._statistics_report
        self.assertEqual(len(report.figures), 6)
        axes = report.figures[0].axes
        histogram = next(axis for axis in axes if axis.get_title() == "WPM distribution")
        self.assertTrue(any(line.get_label() == "Latest session" for line in histogram.lines))
        joint = next(axis for axis in axes if axis.get_title().startswith("Joint WPM"))
        self.assertTrue(any(item.get_label() == "Latest session" for item in joint.collections))
        daily = next(axis for axis in axes if axis.get_title().startswith("Daily averages"))
        self.assertEqual(sum(item.get_label() == "Latest session (individual)"
                             for axis in daily.get_shared_x_axes().get_siblings(daily)
                             for item in axis.collections), 3)
        self.assertEqual(len(report.chapters), 9)
        dividers = [artist for figure in report.figures for artist in figure.artists
                    if artist.get_gid() == "chapter-divider"]
        self.assertEqual(len(dividers), len(report.chapters))
        self.assertLess(report.scroll.yview()[1], 1)
        report.jump(report.canvases[-1].get_tk_widget(), report.figures[-1].axes[0])
        self.root.update()
        self.assertGreater(report.scroll.yview()[0], 0.5)
        report.window.geometry("850x600")
        self.root.update()
        self.assertLessEqual(report.canvases[0].get_tk_widget().winfo_width(), report.scroll.winfo_width())
        output = self.directory / "report.pdf"
        with patch("utils.statistics_report.filedialog.asksaveasfilename", return_value=str(output)):
            report.export_pdf()
        self.assertTrue(output.read_bytes().startswith(b"%PDF"))
        self.app.show_stats()
        self.root.update()
        self.assertFalse(report.window.winfo_exists())

    def test_report_translates_and_restores_chart_titles(self):
        backend.save_wpm_result(self.standard, 50, 1, 20, False, text_details=self.details)
        self.app.show_stats()
        self.root.update()
        report = self.app._statistics_report
        self.app.app_language_var.set("de")
        self.app.change_app_language()
        self.root.update()
        self.assertEqual(report.figures[0].axes[0].get_title(), "WPM-Verteilung")
        self.assertEqual(report.figures[0].axes[0].get_xlabel(), "Wörter pro Minute")
        self.app.app_language_var.set("en")
        self.app.change_app_language()
        self.root.update()
        self.assertEqual(report.figures[0].axes[0].get_title(), "WPM distribution")
        self.assertEqual(report.figures[0].axes[0].get_xlabel(), "Words per minute")

    def test_typing_records_context_in_all_modes_without_unfinished_results(self):
        for mode, path in (("Standard", self.standard), ("Sudden death", self.sudden), ("Blind mode", self.blind)):
            self.app.sudden_death_mode_var.set(mode)
            self.app.on_sudden_death_mode_change()
            self.app._load_text_from_index(0)
            self.root.update()
            self.app.input_text.insert("1.0", self.details["text"])
            self.root.update()
            self.assertTrue(self.app.finished)
            row = read_results(path)[-1]
            self.assertEqual(row["language"], "English")
            self.assertEqual(int(row["text_characters"]), len(self.details["text"]))
            self.assertEqual(int(row["previous_completions"]), ("Standard", "Sudden death", "Blind mode").index(mode))
        self.app.handle_reset_button()
        self.app.input_text.insert("1.0", " ")
        self.root.update()
        self.app.open_text_manager()
        self.root.update()
        self.assertEqual(len(read_results(self.blind)), 1)
