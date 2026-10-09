"""Integration checks. GUI checks must run under the documented isolated Xvfb command."""
import copy
import inspect
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from utils import backend, io_utils, system_theme
from utils.text_manager import visible_whitespace


class TemporaryData:

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.environment = patch.object(io_utils, "get_data_dir", return_value=self.directory)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()


class StorageTests(TemporaryData, unittest.TestCase):
    def test_legacy_library_requires_explicit_language_without_rewriting(self):
        path = io_utils.get__file_path(io_utils.TEXT_FILE_NAME)
        io_utils.write_encrypted(path, json.dumps([{"name": "Old", "text": "Aa 1\n"}]))
        original = path.read_bytes()
        entries = io_utils.load_or_create_texts(path)
        self.assertEqual(entries[0]["language"], "")
        self.assertEqual(path.read_bytes(), original)
        with self.assertRaisesRegex(ValueError, "Language required"):
            io_utils.save_texts(path, entries)
        self.assertEqual(path.read_bytes(), original)
        entries[0]["language"] = "English"
        io_utils.save_texts(path, entries)
        self.assertEqual(io_utils.load_or_create_texts(path), entries)

    def test_coverage_counts_all_languages_exactly_and_includes_zero(self):
        from utils.keyboard_layouts import character_coverage
        entries = [{"text": "Aa 1\t\n", "language": "English"},
                   {"text": "aä1", "language": "German"}]
        rows = dict(character_coverage(entries, "Aaä1? \t\n?", 2))
        self.assertEqual(rows, {"A": 1, "ä": 1, "?": 0, " ": 1, "\t": 1, "\n": 1})
        self.assertEqual(character_coverage(entries, "?", 0), [])

    def test_layout_categories_preserve_superscript_symbols(self):
        from utils.keyboard_layouts import drill_characters, LAYOUTS
        characters = LAYOUTS["German QWERTZ"]
        self.assertIn("²", drill_characters(characters, "special"))
        self.assertIn("³", drill_characters(characters, "special"))
        self.assertIn("ß", drill_characters(characters, "letter"))
        self.assertNotIn(" ", drill_characters(characters, "special"))

    def test_keyboard_preferences_validation(self):
        settings = {"keyboard_layout": "Custom", "custom_characters": "aA? \t\n",
                    "coverage_threshold": 0}
        io_utils.save_settings(settings)
        self.assertEqual(io_utils.load_settings(), settings)
        io_utils.save_settings({"keyboard_layout": "Custom", "custom_characters": "", "coverage_threshold": True})
        self.assertEqual(io_utils.load_settings(), {})

    def test_saving_restricts_languages_to_supported_options(self):
        path = io_utils.get__file_path(io_utils.TEXT_FILE_NAME)
        for language in ("", "-", "French", "english"):
            with self.subTest(language=language), self.assertRaises(ValueError):
                io_utils.save_texts(path, [{"name": "Text", "text": "Content", "language": language}])
        for language in ("English", "German"):
            entries = [{"name": "Text", "text": "Content", "language": language}]
            io_utils.save_texts(path, entries)
            self.assertEqual(io_utils.load_or_create_texts(path), entries)

    def test_empty_library_and_exact_roundtrip(self):
        path = io_utils.get__file_path(io_utils.TEXT_FILE_NAME)
        self.assertEqual(io_utils.load_or_create_texts(path), [])
        entries = [{"name": "Unicode ä", "language": "German", "text": " leading \t\n\nlast  \n"}]
        io_utils.save_texts(path, entries)
        self.assertEqual(io_utils.load_or_create_texts(path), entries)
        self.assertNotIn(b"leading", path.read_bytes())
        self.assertNotIn(b"Unicode", path.read_bytes())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((path.parent / "storage.key").stat().st_mode), 0o600)
        io_utils.save_texts(path, [])
        self.assertEqual(io_utils.load_or_create_texts(path), [])

    def test_tampering_is_rejected_and_not_overwritten(self):
        path = io_utils.get__file_path(io_utils.STATS_FILE_NAME)
        backend.save_wpm_result(path, 50, 2, 20, False)
        content = bytearray(path.read_bytes())
        content[40] ^= 1
        path.write_bytes(content)
        with self.assertRaises(io_utils.DataError):
            backend.save_wpm_result(path, 90, 0, 10, True)
        self.assertEqual(path.read_bytes(), bytes(content))

    def test_missing_key_is_not_regenerated(self):
        path = io_utils.get__file_path(io_utils.TEXT_FILE_NAME)
        io_utils.save_texts(path, [])
        key = path.parent / "storage.key"
        key.unlink()
        with self.assertRaisesRegex(io_utils.DataError, "encryption key is missing"):
            io_utils.load_or_create_texts(path)
        self.assertFalse(key.exists())

    def test_ciphertext_cannot_be_swapped_between_files(self):
        first = io_utils.get__file_path(io_utils.STATS_FILE_NAME)
        second = io_utils.get__file_path(io_utils.LETTER_STATS_FILE_NAME)
        backend.save_wpm_result(first, 50, 2, 20, False)
        second.write_bytes(first.read_bytes())
        with self.assertRaises(io_utils.DataError):
            io_utils.read_encrypted(second)

    def test_all_twelve_statistics_writers_and_append(self):
        for name, function in inspect.getmembers(backend, inspect.isfunction):
            if not name.startswith("save_"):
                continue
            path = io_utils.get__file_path(name + ".csv")
            arguments = {key: (path if key == "file_path" else True if key in ("completed", "is_training_run") else 10)
                         for key in inspect.signature(function).parameters}
            function(**arguments)
            function(**arguments)
            with io_utils.open_encrypted_stats(path) as stream:
                rows = stream.read().splitlines()
            self.assertEqual(len(rows), 3, name)
            self.assertEqual(rows[1].split(";")[-1], "1")
            self.assertNotIn(rows[1].encode(), path.read_bytes())
        self.assertEqual(len(list(io_utils.get_data_dir().glob("*.enc"))), 12)

    def test_settings_roundtrip_and_validation(self):
        expected = {"theme": "dark", "font_size": 20, "ui_font_size": 14, "window_size": "1000x650"}
        io_utils.save_settings(expected)
        self.assertEqual(io_utils.load_settings(), expected)
        path = io_utils.get_data_dir() / "settings.json"
        path.write_text('{"theme":"bad","font_size":true,"window_size":"garbage","training":true}')
        self.assertEqual(io_utils.load_settings(), {})
        path.write_text("broken")
        self.assertEqual(io_utils.load_settings(), {})

    def test_visible_whitespace(self):
        self.assertEqual(visible_whitespace(" a\t\n\n"), "·a⇥↵\n↵\n")
        self.assertIn("U+00A0", visible_whitespace("\u00a0"))
        self.assertIn("U+200B", visible_whitespace("\u200b"))


class SystemThemeTests(unittest.TestCase):
    @patch.object(system_theme.sys, "platform", "linux")
    def test_portal_preference(self):
        for response, expected in (("(<uint32 1>,)", True), ("(<uint32 2>,)", False)):
            with patch.object(system_theme, "_query", return_value=response):
                self.assertEqual(system_theme.system_prefers_dark(), expected)

    @patch.object(system_theme.sys, "platform", "linux")
    def test_gnome_fallback_and_unavailable(self):
        with patch.object(system_theme, "_query", side_effect=["", "'prefer-dark'"]):
            self.assertTrue(system_theme.system_prefers_dark())
        with patch.object(system_theme, "_query", return_value=""):
            self.assertFalse(system_theme.system_prefers_dark())

    @patch.object(system_theme.sys, "platform", "darwin")
    def test_macos(self):
        with patch.object(system_theme, "_query", return_value="Dark"):
            self.assertTrue(system_theme.system_prefers_dark())


@unittest.skipUnless(os.environ.get("TYPING_PRACTICE_TEST_DISPLAY") == "isolated", "GUI checks require isolated Xvfb")
class GuiTests(TemporaryData, unittest.TestCase):
    def setUp(self):
        super().setUp()
        import tkinter as tk
        from utils.ui_utils import TypingTrainerApp
        self.detector = patch.object(TypingTrainerApp, "_detect_system_dark_mode", return_value=False)
        self.detector.start()
        self.root = tk.Tk()
        self.app = TypingTrainerApp(self.root, [])
        self.root.update()
        self.errors = patch("tkinter.messagebox.showerror")
        self.mock_error = self.errors.start()

    def tearDown(self):
        if self.root.winfo_exists():
            if self.app.text_manager:
                self.app.text_manager.saved_entries = copy.deepcopy(self.app.text_manager.entries)
            self.app.close()
        self.errors.stop()
        self.detector.stop()
        super().tearDown()

    def finish_mock_generation(self):
        import time
        deadline = time.monotonic() + 3
        while self.app._generation_pending and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(self.app._generation_pending)

    def test_generated_passages_are_temporary_and_reset_always_requests_new_text(self):
        from utils.io_utils import open_encrypted_stats
        first = "A natural paragraph. " * 20
        second = "A different paragraph. " * 18
        with patch("utils.ui_utils.generate_passage", side_effect=[first, second]) as generate:
            self.app.generate_text_button.invoke()
            self.finish_mock_generation()
            self.assertTrue(self.app._generated_text)
            self.assertEqual(self.app.target_text, first)
            self.assertEqual(self.app.text_entries, [])
            self.assertEqual(self.app.text_manager.entries, [])
            self.assertEqual(self.app.text_listbox.size(), 0)
            self.app.input_text.insert("1.0", first)
            self.root.update()
            self.app.update_typing_state()
            self.assertTrue(self.app.finished)
            with open_encrypted_stats(self.app.stats_file_path) as statistics:
                self.assertEqual(len(statistics.read().splitlines()), 2)
            self.app.handle_reset_button()
            self.assertEqual(self.app.input_text.cget("state"), "disabled")
            self.finish_mock_generation()
            self.assertEqual(self.app.target_text, second)
            self.assertEqual(generate.call_count, 2)
            self.assertEqual(generate.call_args.args[0], "German")
            for file in self.directory.glob("*.enc"):
                self.assertNotIn(first, io_utils.read_encrypted(file))

    def test_selecting_saved_text_discards_late_generation_result(self):
        import threading
        started, release = threading.Event(), threading.Event()
        def generate(language, progress):
            started.set()
            release.wait(3)
            return "Temporary result. " * 24
        self.app.text_entries = [{"name": "Saved", "text": "Keep this text", "language": "English"}]
        self.app.refresh_text_list()
        self.app._load_text_from_index(0)
        with patch("utils.ui_utils.generate_passage", side_effect=generate) as mock:
            self.app.on_generate_text()
            self.assertTrue(started.wait(1))
            self.app.on_generate_text()
            self.assertEqual(mock.call_count, 1)
            self.app._load_text_from_index(0)
            release.set()
            self.finish_mock_generation()
        self.assertEqual(self.app.target_text, "Keep this text")
        self.assertFalse(self.app._generated_text)
        self.assertEqual(str(self.app.generate_text_button.cget("state")), "normal")

    def test_generation_failure_keeps_saved_passage_and_closing_does_not_unload(self):
        from utils.text_generation import GenerationError
        self.app.text_entries = [{"name": "Saved", "text": "Original text", "language": "English"}]
        self.app.refresh_text_list()
        self.app._load_text_from_index(0)
        with patch("utils.ui_utils.generate_passage", side_effect=GenerationError("Model could not load")):
            self.app.on_generate_text()
            self.finish_mock_generation()
        self.assertEqual(self.app.target_text, "Original text")
        self.mock_error.assert_called_once()
        with patch("utils.text_generation.subprocess.run") as command, patch.object(self.root, "destroy"):
            self.app.close()
            command.assert_not_called()

    def test_generated_passage_is_not_reused_after_mode_or_helper_switch(self):
        with patch("utils.ui_utils.generate_passage", side_effect=["First text. " * 34, "Second text. " * 33]) as generate:
            self.app.on_generate_text()
            self.finish_mock_generation()
            self.app.sudden_death_mode_var.set("Blind mode")
            self.app.on_sudden_death_mode_change()
            self.finish_mock_generation()
            self.assertEqual(generate.call_count, 2)
            self.assertEqual(self.app.target_text, "Second text. " * 33)
            self.app.start_letter_mode()
            self.app._choose_practice("typing")
            self.assertFalse(self.app._generated_text)
            self.assertEqual(self.app.target_text, "")

    def test_language_dropdown_is_readonly_and_dash_means_unassigned(self):
        manager = self.app.text_manager
        manager.add()
        manager.body.insert("1.0", "Sample passage")
        self.assertEqual(tuple(manager.language_entry.cget("values")), ("-", "English", "German"))
        self.assertEqual(str(manager.language_entry.cget("state")), "readonly")
        self.assertEqual(manager.language_var.get(), "-")
        manager.language_entry.insert(0, "French")
        self.assertEqual(manager.language_var.get(), "-")
        manager.language_entry.current(1)
        self.assertTrue(manager.save())
        manager.add()
        manager.body.insert("1.0", "Second passage")
        manager.language_entry.current(2)
        manager.show_entry(0)
        self.assertEqual(str(manager.language_entry.cget("state")), "readonly")
        self.assertEqual(manager.language_var.get(), "English")
        manager.language_entry.current(0)
        self.assertEqual(manager.entries[0]["language"], "")
        self.assertIn("Language required", manager.listbox.get(0))
        self.assertFalse(manager.save())

    def test_coverage_table_and_headings_follow_live_theme_changes(self):
        from utils.ui_utils import DARK_THEME, LIGHT_THEME
        manager = self.app.text_manager
        self.app.theme_var.set("Dark")
        self.app.change_theme()
        manager.open_coverage()
        for preference, theme in (("Dark", DARK_THEME), ("Light", LIGHT_THEME), ("Dark", DARK_THEME)):
            self.app.theme_var.set(preference)
            self.app.change_theme()
            self.root.update()
            self.assertEqual(manager.coverage_window.cget("background"), theme["background"])
            self.assertEqual(manager.coverage_table.cget("style"), "Coverage.Treeview")
            for option in ("background", "fieldbackground"):
                self.assertEqual(self.app.style.lookup("Coverage.Treeview", option), theme["surface"])
            self.assertEqual(self.app.style.lookup("Coverage.Treeview", "foreground"), theme["text"])
            self.assertEqual(self.app.style.lookup("Coverage.Treeview", "background", ("selected",)), theme["select_background"])
            self.assertEqual(self.app.style.lookup("Coverage.Treeview.Heading", "background"), theme["button_background"])
            self.assertEqual(self.app.style.lookup("Coverage.Treeview.Heading", "foreground"), theme["text"])
            self.assertEqual(self.app.style.lookup("Coverage.Treeview.Heading", "background", ("active",)), theme["button_active_background"])
        manager.coverage_window.destroy()
        manager.open_coverage()
        self.assertEqual(manager.coverage_window.cget("background"), DARK_THEME["background"])

    def test_language_required_and_coverage_ignores_drafts(self):
        self.app.open_text_manager()
        manager = self.app.text_manager
        manager.add()
        manager.body.insert("1.0", "aA1 \t\n")
        self.assertIn("Language required", manager.listbox.get(0))
        self.assertFalse(manager.save())
        manager.language_var.set("English")
        self.assertTrue(manager.save())
        manager.open_coverage()
        def counts():
            return {manager.coverage_table.item(i, "values")[1]: int(manager.coverage_table.item(i, "values")[2])
                    for i in manager.coverage_table.get_children()}
        self.assertEqual(counts()["U+0061"], 1)
        manager.body.insert("end", "aaa")
        manager.refresh_coverage()
        self.assertEqual(counts()["U+0061"], 1)
        self.assertTrue(manager.save())
        self.assertEqual(counts()["U+0061"], 4)
        manager.threshold_var.set("4")
        manager.apply_threshold()
        self.assertNotIn("U+0061", counts())
        manager.threshold_var.set("bad")
        manager.apply_threshold()
        self.assertEqual(self.app.coverage_threshold, 4)
        self.assertIn("whole number", manager.coverage_status.get())
        self.app.keyboard_layout_var.set("US QWERTY")
        self.app.change_keyboard_layout()
        self.assertNotIn("U+00E4", counts())
        self.assertIn("U+000A", counts())
        self.app.keyboard_layout_var.set("German QWERTZ")
        self.app.change_keyboard_layout()
        self.assertEqual(counts()["U+00E4"], 0)

    def test_click_loads_and_completed_input_is_immutable_until_reset(self):
        self.app.text_entries = [{"name": "One", "text": "abc", "language": "English"},
                                 {"name": "Two", "text": "xyz", "language": "German"}]
        self.app.refresh_text_list()
        self.app.text_listbox.selection_set(0)
        self.app.text_listbox.event_generate("<<ListboxSelect>>")
        self.root.update()
        self.assertEqual(self.app.target_text, "abc")
        self.app.input_text.insert("1.0", "abc")
        self.root.update()
        self.app.update_typing_state()
        self.assertTrue(self.app.finished)
        self.assertEqual(self.app.input_text.cget("state"), "disabled")
        self.app.input_text.delete("1.0", "end")
        self.app.input_text.insert("end", "changed")
        self.app.input_text.event_generate("<<Paste>>")
        self.assertEqual(self.app.input_text.get("1.0", "end-1c"), "abc")
        self.app.handle_reset_button()
        self.assertEqual(self.app.input_text.cget("state"), "normal")
        self.assertEqual(self.app.input_text.get("1.0", "end-1c"), "")
        self.app.text_listbox.selection_clear(0, "end")
        self.app.text_listbox.selection_set(1)
        self.app.text_listbox.event_generate("<<ListboxSelect>>")
        self.root.update()
        self.assertEqual(self.app.target_text, "xyz")
        self.app.input_text.insert("end", "x")
        self.app.handle_sudden_death_text_failure(0)
        self.assertEqual(self.app.input_text.cget("state"), "disabled")
        self.app.on_load_random()
        self.assertEqual(self.app.input_text.cget("state"), "normal")

    def test_helper_results_lock_in_all_modes_and_layouts_keep_categories(self):
        import time
        for mode in ("Standard", "Sudden death", "Blind mode"):
            self.app.sudden_death_mode_var.set(mode)
            self.app.on_sudden_death_mode_change(None)
            for kind in ("letter", "special", "number"):
                with self.subTest(mode=mode, kind=kind):
                    self.app.keyboard_layout_var.set("US QWERTY")
                    getattr(self.app, f"start_{kind}_mode")()
                    pool = self.app._drill_characters
                    self.assertNotIn("ä", pool)
                    self.assertTrue(all(c.isalpha() if kind == "letter" else c.isdecimal() if kind == "number"
                                        else not c.isalnum() and not c.isspace() for c in pool))
                    self.app.start_time = time.time() - 1
                    getattr(self.app, f"{kind}_input_history").append(pool[0])
                    getattr(self.app, f"finish_{kind}_mode_session")(sudden_death=mode == "Sudden death")
                    self.assertEqual(self.app.input_text.cget("state"), "disabled")
                    before = self.app.input_text.get("1.0", "end-1c")
                    self.app.input_text.delete("1.0", "end")
                    self.assertEqual(self.app.input_text.get("1.0", "end-1c"), before)
                    self.app.handle_reset_button()
                    self.assertEqual(self.app.input_text.cget("state"), "normal")
        self.app.custom_characters_editor.delete("1.0", "end")
        self.app.custom_characters_editor.insert("1.0", "aA?1")
        self.app.apply_custom_characters()
        for kind in ("letter", "special", "number"):
            getattr(self.app, f"start_{kind}_mode")()
            self.assertEqual(len(getattr(self.app, f"{kind}_sequence")), 100)
        self.app.custom_characters_editor.delete("1.0", "end")
        self.app.custom_characters_editor.insert("1.0", "1")
        self.app.apply_custom_characters()
        with patch("tkinter.messagebox.showinfo") as info:
            self.app.start_letter_mode()
            info.assert_called_once()

    def test_edit_order_save_delete_and_exact_loaded_content(self):
        self.app.open_text_manager()
        manager = self.app.text_manager
        for name, text in (("First", " leading\t\n\ntrailing  \n"), ("Second", "äöü")):
            manager.add()
            manager.language_var.set("German")
            manager.name_var.set(name)
            manager.body.insert("1.0", text)
        manager.move(-1)
        self.assertTrue(manager.save())
        self.assertEqual(self.app.text_listbox.get(0), "01  Second")
        self.app._load_text_from_index(1)
        self.assertEqual(self.app.target_text, " leading\t\n\ntrailing  \n")
        self.assertEqual(io_utils.load_or_create_texts(io_utils.get__file_path(io_utils.TEXT_FILE_NAME)), manager.entries)
        with patch("tkinter.messagebox.askyesno", return_value=True):
            manager.delete()
            manager.delete()
        self.assertTrue(manager.save())
        self.assertEqual(self.app.texts, [])
        self.assertEqual(io_utils.load_or_create_texts(io_utils.get__file_path(io_utils.TEXT_FILE_NAME)), [])
        self.mock_error.assert_not_called()

    def test_drag_reordering_preserves_editor_changes(self):
        from types import SimpleNamespace
        self.app.open_text_manager()
        manager = self.app.text_manager
        for name in ("First", "Second", "Third"):
            manager.add()
            manager.language_var.set("German")
            manager.name_var.set(name)
            manager.body.insert("1.0", name + " text")
        self.root.update()
        first_y = manager.listbox.bbox(0)[1] + 2
        third_y = manager.listbox.bbox(2)[1] + 2
        manager.start_drag(SimpleNamespace(y=first_y))
        manager.drag(SimpleNamespace(y=third_y))
        manager.end_drag(None)
        self.assertTrue(manager.save())
        self.assertEqual([entry["name"] for entry in manager.entries], ["Second", "Third", "First"])
        self.assertEqual(manager.entries[-1]["text"], "First text")

    def test_unsaved_close_cancel_discard_and_validation(self):
        self.app.open_text_manager()
        manager = self.app.text_manager
        manager.add()
        manager.language_var.set("German")
        self.assertFalse(manager.save())  # Empty text rejected.
        with patch("tkinter.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(manager.close())
        with patch("tkinter.messagebox.askyesnocancel", return_value=False):
            self.assertTrue(manager.close())
        self.assertEqual(self.app.texts, [])

    def test_dark_hover_and_live_system_theme(self):
        from utils.ui_utils import DARK_THEME
        self.app.open_text_manager()
        self.app.theme_var.set("Dark")
        self.app.change_theme()
        self.assertTrue(self.app.dark_mode_enabled)
        self.assertEqual(self.app.style.lookup("TCheckbutton", "background", ("active",)), DARK_THEME["background"])
        self.assertEqual(self.app.style.lookup("TButton", "background", ("active",)), DARK_THEME["button_active_background"])
        self.assertEqual(self.app.text_manager.body.cget("background"), DARK_THEME["input_background"])
        self.app.theme_var.set("System")
        self.app.change_theme()
        self.assertFalse(self.app.dark_mode_enabled)
        from concurrent.futures import Future
        future = Future()
        future.set_result(True)
        self.app._theme_future = future
        self.root.after_cancel(self.app._theme_job)
        self.app._poll_system_theme()
        self.assertTrue(self.app.dark_mode_enabled)
        self.assertEqual(self.app.theme_var.get(), "System")

    def test_settings_restore_only_requested_preferences(self):
        self.root.geometry("1100x640")
        self.root.update()
        self.app.increase_font_size()
        self.app.theme_var.set("Dark")
        self.app.change_theme()
        self.app.training_run_var.set(True)
        self.app.close()
        from utils.ui_utils import TypingTrainerApp
        import tkinter as tk
        self.root = tk.Tk()
        self.app = TypingTrainerApp(self.root, [])
        self.root.update()
        self.assertEqual(self.app.current_font_size, 14)
        self.assertEqual(self.app.theme_var.get(), "Dark")
        self.assertEqual((self.root.winfo_width(), self.root.winfo_height()), (1100, 640))
        self.assertFalse(self.app.training_run_var.get())
        self.assertEqual(set(io_utils.load_settings()), {"theme", "font_size", "ui_font_size", "window_size",
                                                         "keyboard_layout", "custom_characters", "coverage_threshold", "generation_language"})

    def test_layout_separates_practice_manager_and_statistics(self):
        self.assertEqual([self.app.app_tabs.tab(tab, "text") for tab in self.app.app_tabs.tabs()],
                         ["Typing", "Text management", "Statistics", "Settings"])
        self.assertTrue(self.app.text_manager.embedded)
        self.assertEqual(self.app.text_manager.window.winfo_toplevel(), self.root)
        self.assertEqual(self.app.training_toggle.master.master, self.app.practice_page)
        self.assertEqual(self.app.sudden_death_mode_combobox.master, self.app.training_toggle.master)

    def test_every_drill_and_submode_has_help_and_typing_switch_clears_helper(self):
        target, boundary = self.load_wrapped_text()
        for mode in ("Standard", "Sudden death", "Blind mode"):
            self.app.sudden_death_mode_var.set(mode)
            self.app.on_sudden_death_mode_change()
            self.app._choose_practice("typing")
            self.assertIn("Typing text", self.app.description_var.get())
            self.assertIn(mode, self.app.description_var.get())
            for name, start in (("Letters", self.app.start_letter_mode),
                                ("Characters", self.app.start_special_mode),
                                ("Numbers", self.app.start_number_mode)):
                start()
                self.assertIn(name, self.app.description_var.get())
                self.assertIn(mode, self.app.description_var.get())
                self.assertEqual(self.app._active_tab_key, "helper")
                self.app._choose_practice("typing")
                self.assertFalse(self.app.is_letter_mode or self.app.is_special_mode or self.app.is_number_mode)
                self.assertEqual(self.app.target_text, target)
                self.assertIn("Typing text", self.app.description_var.get())
                self.assertNotIn("Number mode", self.app.info_text_var.get())
        self.app.training_run_var.set(True)
        self.app._refresh_mode_description()
        self.assertIn("Training run", self.app.description_var.get())

    def test_text_manager_drafts_survive_navigation(self):
        self.app.open_text_manager()
        manager = self.app.text_manager
        manager.add()
        manager.language_var.set("German")
        manager.name_var.set("Draft passage")
        manager.body.insert("1.0", "Unsaved draft text")
        self.root.update()
        self.app.app_tabs.select(self.app.statistics_page)
        self.root.update()
        self.app.open_text_manager()
        self.root.update()
        self.assertIs(self.app.text_manager, manager)
        self.assertEqual(manager.body.get("1.0", "end-1c"), "Unsaved draft text")
        self.assertTrue(manager.save())
        self.assertIn("Draft passage", self.app.text_listbox.get(0))

    def test_statistics_mode_does_not_change_practice(self):
        self.app.start_number_mode()
        self.app.app_tabs.select(self.app.statistics_page)
        self.app.stats_mode_var.set("Blind mode")
        with patch.object(self.app, "_show_blind_stats") as show:
            self.app.show_number_stats()
            show.assert_called_once()
            self.assertEqual(show.call_args.kwargs["file_path"], self.app.blind_number_stats_file_path)
        self.assertEqual(self.app.sudden_death_mode_var.get(), "Standard")
        self.assertTrue(self.app.is_number_mode)

    def test_ui_text_size_is_independent_and_restored(self):
        self.app.change_ui_font_size(3)
        self.assertEqual(self.app.ui_font.actual("size"), 13)
        self.assertEqual(self.app.text_font.actual("size"), 12)
        self.assertEqual(str(self.app.text_manager.name_entry.cget("font")), str(self.app.ui_font))
        self.app.increase_font_size()
        self.assertEqual(self.app.ui_font.actual("size"), 13)
        self.app.close()
        from utils.ui_utils import TypingTrainerApp
        import tkinter as tk
        self.root = tk.Tk()
        self.app = TypingTrainerApp(self.root, [])
        self.root.update()
        self.assertEqual(self.app.ui_font.actual("size"), 13)
        self.assertEqual(self.app.text_font.actual("size"), 14)

    def test_statistics_page_scrolls_when_ui_text_is_larger(self):
        self.root.geometry("1000x550")
        self.app.change_ui_font_size(4)
        self.app.app_tabs.select(self.app.statistics_page)
        self.root.update()
        self.assertLess(self.app.stats_canvas.yview()[1], 1.0)
        self.app.stats_canvas.yview_moveto(1)
        self.assertEqual(self.app.stats_canvas.yview()[1], 1.0)

    def load_wrapped_text(self):
        self.app.text_entries = [{"name": "Wrapping", "text": ("alpha beta gamma delta " * 15) + "\nRequired newline."}]
        self.app.refresh_text_list()
        self.app._load_text_from_index(0)
        self.root.update()
        self.app._capture_soft_wraps()
        self.assertTrue(self.app._soft_wrap_boundaries)
        boundary = min(self.app._soft_wrap_boundaries)
        self.assertEqual(self.app.target_text[boundary - 1], " ")
        return self.app.target_text, boundary

    def test_optional_enter_completion_and_statistics_in_all_modes(self):
        for mode in ("Standard", "Sudden death", "Blind mode"):
            for variant in ("automatic", "replace space", "after space", "before space"):
                with self.subTest(mode=mode, variant=variant):
                    self.app.sudden_death_mode_var.set(mode)
                    self.app.on_sudden_death_mode_change()
                    target, boundary = self.load_wrapped_text()
                    if variant == "automatic":
                        typed = target
                    elif variant == "replace space":
                        typed = target[:boundary - 1] + "\n" + target[boundary:]
                    elif variant == "after space":
                        typed = target[:boundary] + "\n" + target[boundary:]
                    else:
                        typed = target[:boundary - 1] + "\n" + target[boundary - 1:]
                    self.app.input_text.insert("1.0", typed)
                    self.app.start_time = 40
                    with patch("utils.ui_utils.time.time", return_value=100):
                        self.app.update_typing_state()
                    self.assertTrue(self.app.finished)
                    self.assertEqual(self.app.error_count, 0)
                    self.assertFalse(self.app.input_text.tag_ranges("error"))
                    self.assertEqual(self.app.input_text.get("1.0", "end-1c"), typed)
                    self.assertEqual(self.app.target_text, target)
                    path = (self.app.stats_file_path if mode == "Standard" else
                            self.app.sudden_death_typing_stats_file_path if mode == "Sudden death" else
                            self.app.blind_typing_stats_file_path)
                    with io_utils.open_encrypted_stats(path) as stream:
                        row = stream.read().splitlines()[-1].split(";")
                    self.assertEqual(float(row[1]), len(target.split()))
                    if mode == "Blind mode":
                        self.assertEqual(int(row[2]), len(target))
                        self.assertEqual(float(row[5]), 0)

    def test_highlight_and_backspace_use_original_input_positions(self):
        target, boundary = self.load_wrapped_text()
        typed = target[:boundary] + "\nX"
        self.app.input_text.insert("1.0", typed)
        self.app.update_typing_state()
        errors = self.app.input_text.tag_ranges("error")
        self.assertEqual(len(errors), 2)
        self.assertEqual(self.app.input_text.get(*errors), "X")
        self.assertEqual(self.app.error_count, 1)
        self.app.input_text.delete(f"1.0 + {boundary} chars")
        self.app.update_typing_state()
        self.assertEqual(self.app.input_text.get(*self.app.input_text.tag_ranges("error")), "X")
        self.assertEqual(self.app.error_count, 1)

    def test_blind_reveal_marks_actual_error_after_optional_enter(self):
        self.app.sudden_death_mode_var.set("Blind mode")
        self.app.on_sudden_death_mode_change()
        target, boundary = self.load_wrapped_text()
        typed = target[:boundary] + "\nX" + target[boundary + 1:]
        self.app.input_text.insert("1.0", typed)
        self.app.start_time = 40
        self.app.update_typing_state()
        self.assertTrue(self.app.finished)
        self.assertEqual(self.app.input_text.get("1.0", "end-1c"), typed)
        errors = self.app.input_text.tag_ranges("error")
        self.assertEqual(len(errors), 2)
        self.assertEqual(self.app.input_text.get(*errors), "X")
        with io_utils.open_encrypted_stats(self.app.blind_typing_stats_file_path) as stream:
            row = stream.read().splitlines()[-1].split(";")
        self.assertEqual(int(row[2]), len(target))
        self.assertAlmostEqual(float(row[5]), 100 / len(target), places=3)

    def test_sudden_death_failure_uses_canonical_position(self):
        self.app.sudden_death_mode_var.set("Sudden death")
        self.app.on_sudden_death_mode_change()
        target, boundary = self.load_wrapped_text()
        self.app.input_text.insert("1.0", target[:boundary] + "\nX")
        self.app.start_time = 40
        self.app.update_typing_state()
        self.assertTrue(self.app.sudden_death_failure_triggered)
        with io_utils.open_encrypted_stats(self.app.sudden_death_typing_stats_file_path) as stream:
            row = stream.read().splitlines()[-1].split(";")
        self.assertEqual(int(row[2]), boundary)
        self.assertEqual(row[4], "0")

    def test_required_newline_cannot_be_replaced_by_space(self):
        target, boundary = self.load_wrapped_text()
        self.app.input_text.insert("1.0", target.replace("\n", " "))
        self.app.start_time = 40
        self.app.update_typing_state()
        self.assertFalse(self.app.finished)
        self.assertGreater(self.app.error_count, 0)

    def test_wrap_points_are_frozen_until_reset(self):
        target, boundary = self.load_wrapped_text()
        original = self.app._soft_wrap_boundaries.copy()
        self.root.geometry("800x650")
        self.root.update()
        self.app._capture_soft_wraps()
        self.assertEqual(self.app._soft_wrap_boundaries, original)
        self.app.reset_session()
        self.app._capture_soft_wraps()
        self.assertNotEqual(self.app._soft_wrap_boundaries, original)

    def test_modified_input_finishes_without_waiting_for_timer(self):
        target, boundary = self.load_wrapped_text()
        self.app.input_text.insert("1.0", target[:boundary] + "\n" + target[boundary:])
        self.root.update()
        self.assertTrue(self.app.finished)
        self.assertEqual(self.app.error_count, 0)

    def test_charts_read_encrypted_statistics(self):
        import matplotlib.pyplot as plt
        paths = {
            "save_wpm_result": self.app.stats_file_path,
            "save_letter_result": self.app.letter_stats_file_path,
            "save_special_result": self.app.special_stats_file_path,
            "save_number_result": self.app.number_stats_file_path,
            "save_sudden_death_wpm_result": self.app.sudden_death_typing_stats_file_path,
            "save_sudden_death_letter_result": self.app.sudden_death_letter_stats_file_path,
            "save_sudden_death_special_result": self.app.sudden_death_special_stats_file_path,
            "save_sudden_death_number_result": self.app.sudden_death_number_stats_file_path,
            "save_blind_typing_result": self.app.blind_typing_stats_file_path,
            "save_blind_letter_result": self.app.blind_letter_stats_file_path,
            "save_blind_special_result": self.app.blind_special_stats_file_path,
            "save_blind_number_result": self.app.blind_number_stats_file_path,
        }
        for name, path in paths.items():
            writer = getattr(backend, name)
            arguments = {key: (path if key == "file_path" else False if key == "is_training_run"
                               else True if key == "completed" else 10)
                         for key in inspect.signature(writer).parameters}
            writer(**arguments)
        with patch.object(plt, "show"), patch("tkinter.messagebox.showinfo"):
            for mode in ("Standard", "Sudden death", "Blind mode"):
                self.app.stats_mode_var.set(mode)
                for show in (self.app.show_stats, self.app.show_letter_stats,
                             self.app.show_special_stats, self.app.show_number_stats, self.app.show_general_stats):
                    show()
                    plt.close("all")
        self.mock_error.assert_not_called()


if __name__ == "__main__":
    unittest.main()
