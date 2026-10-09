"""Mistake recording across practice modes; GUI only on the isolated display."""
import copy
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from utils import io_utils
from utils.mistake_analysis import load_analysis


@unittest.skipUnless(os.environ.get('TYPING_PRACTICE_TEST_DISPLAY') == 'isolated', 'Requires isolated Xvfb')
class AnalysisGuiTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from utils.ui_utils import TypingTrainerApp
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.data = patch.object(io_utils, 'get_data_dir', return_value=self.directory)
        self.data.start()
        self.theme = patch.object(TypingTrainerApp, '_detect_system_dark_mode', return_value=False)
        self.theme.start()
        self.errors = patch('tkinter.messagebox.showerror')
        self.error = self.errors.start()
        self.root = tk.Tk()
        self.app = TypingTrainerApp(self.root, [])
        self.root.update()

    def tearDown(self):
        self.app.close()
        self.errors.stop()
        self.theme.stop()
        self.data.stop()
        self.temp.cleanup()

    def event(self, char='', keysym='', state=0):
        return SimpleNamespace(char=char, keysym=keysym or char, state=state, widget=self.app.input_text)

    def type(self, char, state=0):
        keysym = 'Return' if char == '\n' else char
        self.app.on_key_press(self.event('\r' if char == '\n' else char, keysym, state))
        self.app.input_text.insert('end', char)
        self.root.update()

    def load(self, text='Ab.'):
        self.app.text_entries = [{'name': 'Test passage', 'text': text, 'language': 'English'}]
        self.app.refresh_text_list()
        self.app._load_text_from_index(0)
        self.root.update()

    def test_typing_corrections_shift_and_analysis_view_filters(self):
        self.load()
        self.type('a')
        self.app.on_key_press(self.event('', 'BackSpace'))
        self.app.input_text.delete('end-2c', 'end-1c')
        self.root.update()
        self.app.on_key_press(self.event('', 'Shift_R'))
        self.type('A', state=1)
        self.app._analysis_key_release(self.event('', 'Shift_R'))
        self.type('b')
        self.type('.')
        self.assertTrue(self.app.finished)
        records = load_analysis()
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record['characters']['A']['first_errors'], 1)
        self.assertEqual(record['shift']['missing_shift'], 1)
        self.assertEqual(record['shift']['opposite_hand'], 1)
        self.assertEqual(record['language'], 'English')
        self.assertEqual(record['corrections']['backspaces'], 1)
        self.assertEqual(record['corrections']['corrected'], 1)
        self.app.show_mistake_analysis()
        view = self.app.analysis_view
        self.assertEqual(view.data['runs'], 1)
        view.minimum.set('1')
        view.variables['History'].set('All history')
        view.refresh()
        self.assertEqual(io_utils.load_settings()['analysis_history'], 'All history')
        self.assertEqual(io_utils.load_settings()['analysis_minimum'], 1)
        self.assertTrue(view.tables['characters'].get_children())
        view.variables['Language'].set('German')
        view.refresh(save=False)
        self.assertEqual(view.data['runs'], 0)
        self.assertIn('No analysis data', view.summary.get())
        self.error.assert_not_called()

    def test_resets_switches_and_closure_never_save_incomplete_data(self):
        self.load('abc')
        self.type('x')
        self.app.handle_reset_button()
        self.assertEqual(load_analysis(), [])
        self.type('a')
        self.app._load_text_from_index(0)
        self.assertEqual(load_analysis(), [])
        self.type('a')
        self.app._choose_practice('helper')
        self.assertEqual(load_analysis(), [])
        self.app.start_number_mode()
        self.type(self.app.number_sequence[0])
        self.app.text_manager.saved_entries = copy.deepcopy(self.app.text_manager.entries)
        with patch.object(self.root, 'destroy'):
            self.app.close()
        self.assertEqual(load_analysis(), [])

    def test_helper_completed_and_sudden_failure_runs_count_only_attempted_targets(self):
        for mode in ('Standard', 'Blind mode', 'Sudden death'):
            self.app.sudden_death_mode_var.set(mode)
            self.app.on_sudden_death_mode_change()
            for kind, sequence in (('letter', 'ab'), ('special', '!?'), ('number', '12')):
                with self.subTest(mode=mode, kind=kind):
                    getattr(self.app, 'start_' + kind + '_mode')()
                    setattr(self.app, kind + '_sequence', list(sequence))
                    setattr(self.app, kind + '_total_letters' if kind == 'letter' else kind + '_total_chars' if kind == 'special' else kind + '_total_digits', 2)
                    self.type('x')
                    if mode == 'Standard':
                        self.type(sequence[0])
                        self.type(sequence[1])
                    elif mode == 'Blind mode':
                        self.type(sequence[1])
                    self.assertTrue(self.app.finished)
                    self.assertIn('First-attempt mistakes:', self.app.stats_summary_var.get())
                    self.assertNotIn('Analysis:', self.app.info_text_var.get())
                    record = load_analysis()[-1]
                    self.assertEqual(record['mode'], kind)
                    self.assertEqual(record['characters'][sequence[0]]['first_errors'], 1)
                    self.assertEqual(sum(v['opportunities'] for v in record['characters'].values()), 1 if mode == 'Sudden death' else 2)
                    self.assertEqual(record['outcome'], 'Sudden-death failure' if mode == 'Sudden death' else 'Completed')
        self.assertEqual(len(load_analysis()), 9)
        self.error.assert_not_called()

    def test_optional_wrap_enter_is_not_recorded_as_mistake(self):
        self.load('aa bb')
        self.app._soft_wrap_boundaries = {3}
        self.app._wraps_captured = True
        for char in 'aa\nbb':
            self.type(char)
        self.assertTrue(self.app.finished)
        record = load_analysis()[0]
        self.assertEqual(sum(record['errors'].values()), 0)
        self.assertEqual(sum(v['opportunities'] for v in record['characters'].values()), 5)

    def test_unknown_shift_and_caps_lock_do_not_become_same_hand_errors(self):
        self.load('AJ')
        self.type('A', state=2)
        self.type('J', state=1)  # Shift was held before input gained focus.
        record = load_analysis()[0]
        self.assertEqual(record['shift']['caps_lock'], 1)
        self.assertEqual(record['shift']['unknown'], 1)
        self.assertNotIn('same_hand', record['shift'])

    def test_typing_blind_and_sudden_death_endings(self):
        self.app.sudden_death_mode_var.set('Blind mode')
        self.app.on_sudden_death_mode_change()
        self.load('abc')
        for char in 'axc':
            self.type(char)
        self.assertTrue(self.app.finished)
        record = load_analysis()[-1]
        self.assertEqual(record['variant'], 'blind')
        self.assertEqual(record['characters']['b']['first_errors'], 1)
        self.assertEqual(record['corrections']['remaining'], 1)
        self.app.sudden_death_mode_var.set('Sudden death')
        self.app.on_sudden_death_mode_change()
        self.load('abc')
        self.type('a')
        self.type('x')
        self.assertTrue(self.app.finished)
        record = load_analysis()[-1]
        self.assertEqual(record['outcome'], 'Sudden-death failure')
        self.assertEqual(sum(v['opportunities'] for v in record['characters'].values()), 2)
        self.assertNotIn('c', record['characters'])

    def test_native_tk_shift_events_record_side_without_accuracy_penalty(self):
        self.app.sudden_death_mode_var.set('Sudden death')
        self.app.on_sudden_death_mode_change()
        self.load('A')
        self.app.input_text.focus_force()
        self.root.update()
        self.app.input_text.event_generate('<KeyPress>', keysym='Shift_L')
        self.app.input_text.event_generate('<KeyPress>', keysym='A', state=1)
        self.app.input_text.event_generate('<KeyRelease>', keysym='Shift_L', state=1)
        self.root.update()
        self.assertTrue(self.app.finished)
        record = load_analysis()[-1]
        self.assertEqual(record['shift']['same_hand'], 1)
        self.assertEqual(record['characters']['A']['first_errors'], 0)
        self.assertEqual(record['outcome'], 'Completed')

    def test_pasted_input_is_excluded_without_changing_normal_statistics(self):
        self.load('abc')
        self.app._analysis_bulk_edit()
        self.app.input_text.insert('1.0', 'abc')
        self.root.update()
        self.app.update_typing_state()
        self.assertTrue(self.app.finished)
        self.assertEqual(load_analysis(), [])
        self.assertTrue(self.app.stats_file_path.exists())
        self.assertIsNone(self.app._current_session_analysis)
        self.assertTrue(self.app.session_mistakes_button.instate(['disabled']))
        self.assertIn('analysis unavailable', self.app.stats_summary_var.get())
        self.assertNotIn('Analysis unavailable', self.app.info_text_var.get())

    def test_current_session_report_is_independent_of_history_and_preferences(self):
        self.load('abc')
        for char in 'abc':
            self.type(char)
        self.load('Ab')
        self.type('a')
        self.app.input_text.delete('1.0', 'end')
        self.root.update()
        self.type('A', state=1)
        self.type('b')
        self.assertEqual(len(load_analysis()), 2)
        self.app.analysis_history = 'Last 7 days'
        self.app.analysis_minimum = 1000
        self.app.analysis_view.variables['Language'].set('German')
        self.app.analysis_view.refresh(save=False)
        self.assertEqual(self.app.analysis_view.data['runs'], 0)
        selected_tab = self.app.app_tabs.select()
        with patch('utils.analysis_view.load_analysis', side_effect=AssertionError('Session report must not load history')), patch.object(self.app, '_save_preferences') as save:
            self.app.session_mistakes_button.invoke()
            self.root.update()
            view = self.app.session_analysis_view
            self.assertEqual(view.data['runs'], 1)
            self.assertEqual(set(view.data['characters']), {'A', 'b'})
            self.assertEqual(view.data['characters']['A']['first_errors'], 1)
            self.assertEqual(view.variables, {})
            self.assertFalse(hasattr(view, 'minimum'))
            self.assertNotIn('progress', view.tables)
            self.assertNotIn('Evidence', view.tables['characters']['columns'])
            self.assertIn('This session', view.summary.get())
            view.refresh()
            save.assert_not_called()
        self.assertEqual(self.app.app_tabs.select(), selected_tab)
        self.assertIn('First-attempt mistakes: 1/2', self.app.stats_summary_var.get())
        self.assertNotIn('Analysis:', self.app.info_text_var.get())
        window = self.app.session_analysis_window
        self.app.session_mistakes_button.invoke()
        self.assertIs(self.app.session_analysis_window, window)
        self.app.handle_reset_button()
        self.assertFalse(window.winfo_exists())
        self.assertIsNone(self.app.session_analysis_view)
        self.assertIsNone(self.app._current_session_analysis)
        self.assertTrue(self.app.session_mistakes_button.instate(['disabled']))
        self.assertNotIn('First-attempt mistakes:', self.app.stats_summary_var.get())

    def test_current_report_survives_history_save_failure_and_can_be_reopened(self):
        self.load('abc')
        with patch('utils.ui_utils.save_analysis', side_effect=OSError('Test save failure')):
            for char in 'abc':
                self.type(char)
        self.error.assert_called_once()
        self.assertIsNotNone(self.app._current_session_analysis)
        self.app.show_current_session_mistakes()
        self.app._close_session_analysis()
        self.app.show_current_session_mistakes()
        self.assertEqual(self.app.session_analysis_view.data['runs'], 1)
        self.assertEqual(load_analysis(), [])
