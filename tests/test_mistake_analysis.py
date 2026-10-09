"""Analytic semantics, exposure denominators, privacy, and completed-run persistence."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from utils import io_utils
from utils.keyboard_layouts import character_key
from utils.mistake_analysis import MistakeRecorder, align_prefix, aggregate, filter_records, findings, save_analysis, load_analysis, ANALYSIS_FILE

META = {"layout": "German QWERTZ", "mode": "typing", "variant": "standard", "language": "German", "training": False, "source": "generated", "outcome": "Completed"}


def recorder(target, **kwargs):
    return MistakeRecorder(target, {**META, **kwargs})


class AnalysisTests(unittest.TestCase):
    def test_alignment_avoids_omission_and_extra_cascades(self):
        mapping, gaps, swaps = align_prefix('abcdef', 'abdef')
        self.assertEqual(mapping, [0, 1, 3, 4, 5])
        self.assertEqual(gaps, {2})
        mapping, gaps, swaps = align_prefix('abcdef', 'abXcdef')
        self.assertEqual(mapping, [0, 1, None, 2, 3, 4, 5])
        self.assertEqual(gaps, set())
        self.assertEqual(align_prefix('abcdef', 'x')[0], [0])
        mapping, gaps, swaps = align_prefix('the', 'hte')
        self.assertEqual(mapping, [0, 1, 2])
        self.assertEqual(swaps, {(0, 1)})

    def test_corrected_capitalization_survives_backspace_and_is_first_attempt_error(self):
        run = recorder('Ab')
        run.observe('a', {"shift": "none", "caps": False})
        run.backspace()
        run.observe('')
        run.observe('A', {"shift": "left", "caps": False})
        run.observe('Ab')
        result = run.finish()
        self.assertEqual(result['characters']['A']['opportunities'], 1)
        self.assertEqual(result['characters']['A']['first_errors'], 1)
        self.assertEqual(result['errors']['missing_capital'], 1)
        self.assertEqual(result['shift']['missing_shift'], 1)
        self.assertEqual(result['shift']['same_hand'], 1)
        self.assertEqual(result['corrections']['corrected'], 1)
        self.assertEqual(result['corrections']['backspaces'], 1)
        self.assertEqual(result['corrections']['remaining'], 0)

    def test_corrected_transposition_is_one_type_event_with_two_wrong_positions(self):
        run = recorder('the')
        for text in ('h', 'ht', 'hte', '', 't', 'th', 'the'):
            run.observe(text)
        result = run.finish()
        self.assertEqual(result['errors']['transpose'], 1)
        self.assertEqual(sum(v['first_errors'] for v in result['characters'].values()), 2)
        self.assertEqual(result['corrections']['corrected'], 2)
        self.assertEqual(result['confusions'], [])

    def test_omissions_extras_and_repeats_are_separate_from_character_confusions(self):
        run = recorder('abc')
        run.observe('ac')
        result = run.finish()
        self.assertEqual(result['errors']['omission'], 1)
        self.assertEqual(result['characters']['b']['first_errors'], 1)
        self.assertEqual(result['characters']['c']['first_errors'], 0)
        run = recorder('abc')
        run.observe('aabc')
        result = run.finish()
        self.assertEqual(result['errors']['repeat'], 1)
        self.assertEqual(result['confusions'], [])

    def test_helper_retries_count_one_first_failure_and_all_mistakes(self):
        run = recorder('a1!')
        run.attempt(0, 'a', 's')
        run.attempt(0, 'a', 'd')
        run.attempt(0, 'a', 'a')
        run.attempt(1, '1', '1')
        run.attempt(2, '!', '!', {"shift": "right", "caps": False})
        result = run.finish()
        self.assertEqual(result['characters']['a']['first_errors'], 1)
        self.assertEqual(result['characters']['a']['mistakes'], 2)
        self.assertEqual(result['corrections']['corrected'], 2)
        self.assertEqual(result['characters']['!']['opportunities'], 1)
        self.assertEqual(result['shift']['opposite_hand'], 1)

    def test_caps_unknown_and_custom_mapping_do_not_invent_technique_errors(self):
        run = recorder('AJZ')
        run.attempt(0, 'A', 'A', {"shift": "none", "caps": True})
        run.attempt(1, 'J', 'J', {"shift": "unknown", "caps": False})
        run.attempt(2, 'Z', 'Z', {"shift": "left", "caps": False})
        result = run.finish()
        self.assertEqual(result['shift']['caps_lock'], 1)
        self.assertEqual(result['shift']['unknown'], 1)
        self.assertEqual(result['shift']['opposite_hand'], 1)  # German Z belongs to right hand.
        self.assertNotIn('same_hand', result['shift'])
        self.assertEqual(character_key('Y', 'German QWERTZ')[1], 'left')
        self.assertEqual(character_key('Y', 'US QWERTY')[1], 'right')
        run = recorder('A', layout='Custom')
        run.attempt(0, 'A', 'A', {"shift": "left", "caps": False})
        self.assertEqual(run.finish()['shift']['unknown'], 1)

    def test_timing_excludes_pauses_and_preserves_transition_samples(self):
        now = [0.0]
        run = MistakeRecorder('abc', META, clock=lambda: now[0])
        run.observe('a')
        now[0] = 0.2
        run.observe('ab')
        now[0] = 20
        run.observe('abc')
        result = run.finish()
        self.assertEqual(result['characters']['b']['delay_ms'], 200)
        self.assertEqual(result['characters']['c']['delay_count'], 0)
        self.assertEqual(result['transitions'], [['ab', 1, 200.0]])
        self.assertEqual(result['pauses'], 1)

    def test_filters_ranking_and_exposure_denominators(self):
        run = recorder('e' * 40)
        for index in range(40):
            run.attempt(index, 'e', 'r' if index == 0 else 'e')
        a = run.finish()
        run = recorder(';')
        run.attempt(0, ';', 'l')
        b = run.finish()
        a['timestamp'] = datetime.now(timezone.utc).isoformat()
        b['timestamp'] = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        b.update(mode='special', layout='US QWERTY', language='English', training=True)
        self.assertEqual(len(filter_records([a,b])), 1)
        self.assertEqual(filter_records([a,b], history='All history', mode='special', training='Training'), [b])
        data = aggregate([a,b])
        self.assertIn("'e'", findings(data, minimum=30)[0])
        self.assertIn('2.5%', findings(data, minimum=30)[0])

    def test_encrypted_history_contains_aggregates_and_no_passage(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(io_utils,'get_data_dir',return_value=Path(directory)):
            passage='A private temporary passage that must not persist.'
            run=recorder(passage)
            for index,char in enumerate(passage):
                run.attempt(index,char,char)
            record=run.finish()
            save_analysis(record)
            self.assertEqual(load_analysis(),[record])
            path=io_utils.get__file_path(ANALYSIS_FILE)
            self.assertNotIn(passage.encode(),path.read_bytes())
            self.assertNotIn(passage,io_utils.read_encrypted(path))
            original=path.read_bytes()
            path.write_bytes(original[:-3]+b'bad')
            with self.assertRaises(io_utils.DataError):
                save_analysis(record)
            self.assertEqual(path.read_bytes(),original[:-3]+b'bad')

    def test_excluded_bulk_input_produces_no_record(self):
        run=recorder('abc')
        run.observe('abc')
        run.excluded=True
        self.assertIsNone(run.finish())
